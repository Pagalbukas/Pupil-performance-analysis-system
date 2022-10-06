from __future__ import annotations

import datetime
import logging
import os

import matplotlib # type: ignore

# Tell matplotlib to use QtAgg explicitly
matplotlib.use('QtAgg')

from types import MethodType
from typing import (
    TYPE_CHECKING,
    Dict, List
)

import matplotlib.cm as mplcm  # type: ignore # noqa: E402
import matplotlib.colors as colors  # type: ignore # noqa: E402
import matplotlib.patheffects as path_effects  # type: ignore # noqa: E402
import matplotlib.pyplot as plt  # type: ignore # noqa: E402
# For tweaking the default UI
from matplotlib.backend_bases import PickEvent, NavigationToolbar2  # type: ignore # noqa: E402
from matplotlib.backends.backend_qt import NavigationToolbar2QT  # type: ignore # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvas # type: ignore # noqa: E402
# The modules exist, but for some reason, they are not picked up by Pylance
from matplotlib.backends.qt_compat import (  # type: ignore # noqa: E402
    QtWidgets, _getSaveFileName
)
from matplotlib.figure import Figure  # type: ignore # noqa: E402
from matplotlib.legend_handler import HandlerLine2D  # type: ignore # noqa: E402
from matplotlib.lines import Line2D  # type: ignore # noqa: E402
from matplotlib.text import Annotation  # type: ignore # noqa: E402

from analyser.graphing import BaseGraph
from analyser.qt_compat import Qt

MONTH_NAMES = {
    1: "Sausis",
    2: "Vasaris",
    3: "Kovas",
    4: "Balandis",
    5: "Gegužė",
    6: "Birželis",
    7: "Liepa",
    8: "Rugpjūtis",
    9: "Rugsėjis",
    10: "Spalis",
    11: "Lapkritis",
    12: "Gruodis"
}

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

# Modify default save figure to have more fine-grained control over available file formats
def save_figure(self, *args):
    filetypes = {
        'PDF failas (rekomenduojama)': ['pdf'],
        'Nuotrauka (aukštos kokybės)': ['png'],
        'Nuotrauka (žemos kokybės)': ['jpeg', 'jpg']
    }

    startpath = os.path.expanduser(matplotlib.rcParams['savefig.directory'])


    def get_default_filename():
        """
        Return a string, which includes extension, suitable for use as
        a default filename.
        """
        return (self.canvas.parent().windowTitle() or 'image').replace(' ', '_') + f'_{int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())}'

    start = os.path.join(startpath, get_default_filename() + ".pdf")
    filters = []
    selectedFilter = None
    for name, exts in filetypes.items():
        exts_list = " ".join(['*.%s' % ext for ext in exts])
        filter = '%s (%s)' % (name, exts_list)
        if "pdf" in exts:
            selectedFilter = filter
        filters.append(filter)
    filters = ';;'.join(filters)

    fname, filter = _getSaveFileName(
        self.canvas.parent(), "Pasirinkite failo vardą ir vietą, kur jį išsaugosite", start,
        filters, selectedFilter)

    if fname:
        # Save dir for next time, unless empty str (i.e., use cwd).
        if startpath != "":
            matplotlib.rcParams['savefig.directory'] = (
                os.path.dirname(fname))
        try:
            self.canvas.figure.savefig(fname)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Failo išsaugoti nepavyko", str(e),
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)

def home(self: NavigationToolbar2, *args):
    self._nav_stack.home()
    self.set_history_buttons()
    update_line_visibility = getattr(self.canvas.toolbar, "update_line_visibility")
    update_line_visibility()
    self._update_view()

class MatplotlibWindow(QtWidgets.QMainWindow):

    LINE_STYLES = ['-', '--', '-.', ':']
    STYLE_COUNT = len(LINE_STYLES)

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.app = app

        self.canvas = FigureCanvas(Figure(figsize=(1, 1)))
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        #layout = QVBoxLayout()
        #layout.addWidget(self.toolbar)
        #layout.addWidget(self.canvas)
        #self.setLayout(layout)

        self.addToolBar(self.toolbar)
        self.setCentralWidget(self.canvas)

        cs = self.canvas.sizeHint()
        cs_height = cs.height()
        height = cs_height + self.toolbar.sizeHint().height()
        self.resize(cs.width(), height)

        self.setMinimumWidth(540)
        self.setMinimumHeight(480)
    
    def set_window_flags(self) -> None:
        # Open maximized
        self.setWindowState(Qt.WindowMaximized)

        # Set modality to disallow access to main window while this
        # is shown
        self.setWindowModality(Qt.WindowModal)  

    def clear_figure(self) -> None:
        """Clears the figure of any subplots and values."""
        self.canvas.figure.clear()

    def _setup_figure(self, figure: Figure) -> Figure:
        """Sets up a custom matplotlib figure, the Qt toolbar to be more precise."""
        toolbar: NavigationToolbar2QT = figure.canvas.toolbar

        # Modify instance methods
        toolbar.save_figure = MethodType(save_figure, toolbar)
        toolbar.home = MethodType(home, toolbar)

        # A dict containing toolbar item locale mapping and visibility settings
        item_locales = {
            "Home": ("Pradžia", "Nustatyti atgal į pradinę padėtį", True),
            "Back": ("Atgal", "Grįžti atgal", True),
            "Forward": ("Pirmyn", "Grįžti pirmyn", True),
            "Pan": ("Pan", "Left button pans, Right button zooms\nx/y fixes axis, CTRL fixes aspect", False),
            "Zoom": ("Padidinti", "Padidinti iki stačiakampio\nx/y fiksuoja ašis", True),
            "Subplots": ("Grafikas", "Redaguoti grafiką", True),
            "Customize": ("Customize", "Edit axis, curve and image parameters", False),
            "Save": ("Išsaugoti", "Išsaugoti grafiką", True)
        }

        # Apply the said values to the toolbar actions in this loop
        for action in toolbar.actions():
            if action.text == "":
                continue
            
            val = item_locales.get(action.text(), None)
            if val is not None:
                name, tooltip, show = val
                action.setText(name)
                action.setToolTip(tooltip)
                action.setVisible(show)            
        return figure

    def load_from_graph(self, graph: BaseGraph) -> None:
        self.clear_figure()

        # Store data into local variables for mutation
        x_values, y_values = graph.acquire_axes()
        x_count, y_count = (len(x_values), len(y_values))

        # Create a plot and a figure
        ax = self.canvas.figure.subplots()

        # Set up custom toolbar
        self._setup_figure(self.canvas.figure)

        # Set unique colors for lines in a rainbow fashion
        cm = plt.get_cmap('gist_rainbow')
        if not self.app.settings.styled_colouring:
            c_normalised = colors.Normalize(vmin=0, vmax=y_count - 1)
            scalar_map = mplcm.ScalarMappable(norm=c_normalised, cmap=cm)
            ax.set_prop_cycle(color=[scalar_map.to_rgba(i) for i in range(y_count)])

        # Line object: [array of annotations]
        # Used for removing annotations when hiding lines
        line_bound_annotations: Dict[Line2D, List[Annotation]] = {}

        # Array of line objects
        # Used for selecting line objects
        lines: List[Line2D] = []

        # Graph actual data
        for i, val in enumerate(y_values):
            # Draw a line of student averages
            line = ax.plot(x_values, val.values, marker='o', label=val.label)[0]

            if self.app.settings.styled_colouring:
                # Adapted from https://stackoverflow.com/a/44937195
                line.set_color(cm(i // self.STYLE_COUNT * float(self.STYLE_COUNT) / y_count))
                line.set_linestyle(self.LINE_STYLES[i % self.STYLE_COUNT])

            # Create an array of annotations and draw them
            annotations: List[Annotation] = [None] * x_count
            for j, digit in enumerate(val.values):
                if digit is None:
                    continue

                annotation = ax.annotate(
                    str(digit).replace('.', ','),
                    xy=(x_values[j], digit),
                    color='white' if self.app.settings.outlined_values else 'black',
                    ha="center", va="center"
                )
                if self.app.settings.outlined_values:
                    # https://matplotlib.org/stable/tutorials/advanced/patheffects_guide.html#making-an-artist-stand-out
                    annotation.set_path_effects([
                        path_effects.Stroke(linewidth=2, foreground='black'),
                        path_effects.Normal()
                    ])
                annotations[j] = annotation
            line_bound_annotations[line] = annotations
            lines.append(line)

        # Set labels of the axles using the graph provided names
        x_label, y_label = graph.axis_labels
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        # Adjusts the plot size
        if self.app.settings.corner_legend:
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])

        # Remove markers from the legend
        # Adapted from https://stackoverflow.com/a/48391281
        def update_prop(handle, orig):
            handle.update_from(orig)
            handle.set_marker("")

        # Moves the legend outside of the plot
        if self.app.settings.corner_legend:
            leg = ax.legend(
                handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)},
                loc='center left',
                bbox_to_anchor=(1, 0.5)
            )
        else:
            leg = ax.legend(handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)})

        # Map legend lines to original lines
        lined = {}
        for legline, origline in zip(leg.get_lines(), lines):
            legline.set_picker(True)  # Enable picking on the legend line.
            legline.set_pickradius(7) # Increase picking radius
            lined[legline] = origline

        # https://matplotlib.org/stable/gallery/event_handling/legend_picking.html
        def on_pick(event: PickEvent):
            # On the pick event, find the original line corresponding to the legend
            # proxy line, and toggle its visibility.

            legline: Line2D = event.artist
            origline = lined[legline]
            visible = not origline.get_visible()

            # Set line visibility on the plot
            origline.set_visible(visible)

            # Remove annotations if appropriate
            annotations = line_bound_annotations[origline]
            [a.set(visible=visible) for a in annotations if a is not None] # type: ignore

            # Change the alpha on the line in the legend so we can see what lines
            # have been toggled.
            legline.set_alpha(1.0 if visible else 0.2)
            self.canvas.draw()

        def update_line_visibility():
            # Set every line annotation on the graph to be visible
            for line in line_bound_annotations.keys():
                for annotation in line_bound_annotations[line]:
                    if annotation is not None:
                        annotation.set(visible=True)

            # Set every line on graph to be visible
            for line in lined.keys():
                lined[line].set_visible(True)
            
            # Set every legend line to default alpha value
            for legline in leg.get_lines():
                legline.set_alpha(1.0)

            # Ending draw call to update view
            self.canvas.draw()

        # Bind the pick_event event
        self.canvas.mpl_connect('pick_event', on_pick)
        
        # Add update_line_visibility method to the toolbar
        setattr(self.canvas.toolbar, "update_line_visibility", update_line_visibility)

        # Create a grid of values
        ax.grid(True)

        # Set window and plot name
        self.canvas.figure.suptitle(graph.title, fontsize=16)
        self.setWindowTitle(graph.window_title)

        # Automatically maximise the window
        self.set_window_flags()

        # Call draw method to update in case of old graphs
        self.canvas.draw()
