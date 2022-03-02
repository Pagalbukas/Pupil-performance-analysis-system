import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as mplcm
import matplotlib.colors as colors

from matplotlib.backend_bases import PickEvent
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.lines import Line2D
from random import choice, shuffle
from typing import List, Optional

LINE_STYLES = ['-', '--', '-.', ':']
STYLE_COUNT = len(LINE_STYLES)

class BaseGraph:
    # TODO: subclass from
    pass

class StudentAveragesGraph:

    def __init__(self, period_names: List[str]) -> None:
        self.period_names = period_names
        self.students = {}

    def get_or_create_student(self, student_name: str) -> Optional[float]:
        """Creates or gets a student entry in the dictionary and returns the reference."""
        if self.students.get(student_name) is None:
            self.create_student(student_name)
        return self.get_student(student_name)

    def create_student(self, student_name: str) -> Optional[float]:
        """Creates a student entry in the dictionary and returns the reference."""
        self.students[student_name] = [None] * len(self.period_names)
        return self.get_student(student_name)

    def get_student(self, student_name: str) -> Optional[float]:
        """Returns a reference of a student entry in the dictionary."""
        return self.students[student_name]

    def anonymize_students(self) -> None:
        """Anonymizes the names of students in the graph."""
        names = ["Antanas", "Bernardas", "Cezis", "Dainius", "Ernestas", "Henrikas", "Jonas", "Petras", "Tilius"]
        surnames = ["Antanivičius", "Petraitis", "Brazdžionis", "Katiliškis", "Mickevičius", "Juozevičius", "Eilėraštinis"]
        new_dict = {}
        cached_combinations = []

        # Shuffle student names to avoid being recognized by the position in the legend
        student_names = list(self.students.keys())
        shuffle(student_names)

        for student in student_names:
            name = choice(names) + " " + choice(surnames)
            while name in cached_combinations:
                name = choice(names) + " " + choice(surnames)
            new_dict[name] = self.students[student]
            cached_combinations.append(name)
        self.students = new_dict

    def graph(
        self,
        title: str = None,
        show_bounds: bool = False,
        anonymize_names: bool = False,
        use_styled_colouring: bool = False,
        use_experimental_legend: bool = False
    ) -> None:
        """Instructs matplotlib to draw a graph."""

        # Create a plot and a figure
        fig, ax = plt.subplots()

        # Anonymize names when displaying for unauthorized people, in order to prevent disclosing of any additional data
        if anonymize_names:
            self.anonymize_students()

        # Store data into local variables for mutation
        period_names = self.period_names
        students = self.students
        period_cnt = len(period_names)
        student_cnt = len(students)

        # Set unique colors for lines in a rainbow fashion
        cm = plt.get_cmap('gist_rainbow')
        if not use_styled_colouring:
            c_normalised = colors.Normalize(vmin=0, vmax=student_cnt - 1)
            scalar_map = mplcm.ScalarMappable(norm=c_normalised, cmap=cm)
            ax.set_prop_cycle(color=[scalar_map.to_rgba(i) for i in range(student_cnt)])

        # Draw average rounding bounds
        if show_bounds:
            for i in np.arange(1.5, 10, 0.5):
                i: float
                if not i.is_integer():
                    ax.plot(period_names, [i] * period_cnt, '--r')

        # Line object: [array of annotations]
        # Used for removing annotations when hiding lines
        line_bound_annotations = {}

        # Array of line objects
        # Used for selecting line objects
        lines = []

        # Graph actual data
        for i, name in enumerate(students):
            # Draw a line of student averages
            line = ax.plot(period_names, students[name], marker='o', label=name)[0]

            if use_styled_colouring:
                # Adapted from https://stackoverflow.com/a/44937195
                line.set_color(cm(i // STYLE_COUNT * float(STYLE_COUNT) / student_cnt))
                line.set_linestyle(LINE_STYLES[i % STYLE_COUNT])

            # Create an array of annotations and draw them
            annotations = [None] * period_cnt
            for j, digit in enumerate(students[name]):
                if digit is None:
                    continue

                annotation = ax.annotate(
                    str(digit).replace('.', ','),
                    xy=(period_names[j], digit),
                    ha="center", va="center"
                )
                annotations[j] = annotation
            line_bound_annotations[line] = annotations
            lines.append(line)

        # Set labels and limits of the axles
        ax.set_ylabel('Vidurkis')
        ax.set_ylim(top=10)
        ax.set_xlabel('Laikotarpis')

        # Adjusts the plot size
        if use_experimental_legend:
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])

        # Remove markers from the legend
        # Adapted from https://stackoverflow.com/a/48391281
        def update_prop(handle, orig):
            handle.update_from(orig)
            handle.set_marker("")

        if use_experimental_legend:
            # Moves the legend outside of the plot
            leg = plt.legend(
                handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)},
                loc='center left',
                bbox_to_anchor=(1, 0.5)
            )
        else:
            leg = plt.legend(handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)})

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
            [a.set(visible=visible) for a in annotations if a is not None]

            # Change the alpha on the line in the legend so we can see what lines
            # have been toggled.
            legline.set_alpha(1.0 if visible else 0.2)
            fig.canvas.draw()

        # Bind the pick_event event
        fig.canvas.mpl_connect('pick_event', on_pick)

        # Create a grid of values
        ax.grid(True)

        # If title is provided, set the title of the graph
        if title is not None:
            fig.suptitle(title, fontsize=16)

        plt.gcf().canvas.set_window_title(title or 'Bendras klasės vidurkių grafikas')
        plt.show()
