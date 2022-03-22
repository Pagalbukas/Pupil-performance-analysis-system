import matplotlib

# Tell matplotlib to use Qt5Agg explicitly
matplotlib.use('Qt5Agg')

import matplotlib.cm as mplcm # noqa: E402
import matplotlib.colors as colors # noqa: E402

# For tweaking the default UI
from matplotlib.backend_bases import PickEvent # noqa: E402
from matplotlib.legend_handler import HandlerLine2D # noqa: E402
from matplotlib.lines import Line2D # noqa: E402

# Load the plot last for certain features to work
import matplotlib.pyplot as plt # noqa: E402

from random import choice, shuffle # noqa: E402
from typing import Any, List, Optional, Tuple # noqa: E402

class GraphValue:

    def __init__(self, label: str, values: Any) -> None:
        self.label = label
        self.values = values

    def __repr__(self) -> str:
        return f'<GraphValue label=\'{self.label}\' values={self.values}>'

class BaseGraph:

    LINE_STYLES = ['-', '--', '-.', ':']
    STYLE_COUNT = len(LINE_STYLES)

    def __init__(self, title: str) -> None:
        self.title = title

    def set_limits(self, ax) -> None:
        ax.set_ylim(top=10)
        ax.set_ylabel('Vidurkis')
        ax.set_xlabel('Laikotarpis')

    def acquire_axes(self) -> Tuple[str, List[GraphValue]]:
        raise NotImplementedError

    def display(
        self,
        use_styled_colouring: bool = True,
        use_experimental_legend: bool = False
    ) -> None:
        """Instructs matplotlib to display a graph."""

        # Create a plot and a figure
        fig, ax = plt.subplots()

        # Store data into local variables for mutation
        x_values, y_values = self.acquire_axes()
        x_count, y_count = (len(x_values), len(y_values))

        # Set unique colors for lines in a rainbow fashion
        cm = plt.get_cmap('gist_rainbow')
        if not use_styled_colouring:
            c_normalised = colors.Normalize(vmin=0, vmax=y_count - 1)
            scalar_map = mplcm.ScalarMappable(norm=c_normalised, cmap=cm)
            ax.set_prop_cycle(color=[scalar_map.to_rgba(i) for i in range(y_count)])

        # Line object: [array of annotations]
        # Used for removing annotations when hiding lines
        line_bound_annotations = {}

        # Array of line objects
        # Used for selecting line objects
        lines = []

        # Graph actual data
        for i, val in enumerate(y_values):
            # Draw a line of student averages
            line = ax.plot(x_values, val.values, marker='o', label=val.label)[0]

            if use_styled_colouring:
                # Adapted from https://stackoverflow.com/a/44937195
                line.set_color(cm(i // self.STYLE_COUNT * float(self.STYLE_COUNT) / y_count))
                line.set_linestyle(self.LINE_STYLES[i % self.STYLE_COUNT])

            # Create an array of annotations and draw them
            annotations = [None] * x_count
            for j, digit in enumerate(val.values):
                if digit is None:
                    continue

                annotation = ax.annotate(
                    str(digit).replace('.', ','),
                    xy=(x_values[j], digit),
                    ha="center", va="center"
                )
                annotations[j] = annotation
            line_bound_annotations[line] = annotations
            lines.append(line)

        # Set labels and limits of the axles
        self.set_limits(ax)

        # Adjusts the plot size
        if use_experimental_legend:
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])

        # Remove markers from the legend
        # Adapted from https://stackoverflow.com/a/48391281
        def update_prop(handle, orig):
            handle.update_from(orig)
            handle.set_marker("")

        # Moves the legend outside of the plot
        if use_experimental_legend:
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
        if self.title:
            fig.suptitle(self.title, fontsize=16)

        plt.gcf().canvas.set_window_title(self.title.replace("\n", " "))
        plt.show()


class ClassAveragesGraph(BaseGraph):

    def __init__(self, title: str, period_names: List[str], anonymize_names: bool = False, perform_rounding: bool = False) -> None:
        super().__init__(title)
        self.period_names = period_names
        self.students = {}
        self.anonymize_names = anonymize_names
        self.perform_rounding = perform_rounding

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

    def get_graph_values(self) -> List[GraphValue]:
        if not self.perform_rounding:
            return [GraphValue(n, self.students[n]) for n in self.students.keys()]
        return [
            GraphValue(n, [round(v, 1) for v in self.students[n]])
            for n in self.students.keys()
        ]

    def acquire_axes(self) -> Tuple[str, List[GraphValue]]:
        # Anonymize names when displaying for unauthorized people, in order to prevent disclosing of any additional data
        if self.anonymize_names:
            self.anonymize_students()
        return (self.period_names, self.get_graph_values())


class ClassPeriodAveragesGraph(ClassAveragesGraph):

    def __init__(self, title: str, period_names: List[str], anonymize_names: bool = False, perform_rounding: bool = False) -> None:
        super().__init__(title, period_names, anonymize_names, perform_rounding)

class ClassMonthlyAveragesGraph(ClassAveragesGraph):

    def __init__(self, title: str, period_names: List[str], anonymize_names: bool = False, perform_rounding: bool = False) -> None:
        super().__init__(title, period_names, anonymize_names, perform_rounding)

class PupilSubjectAveragesGraph(BaseGraph):

    def __init__(self, title: str, period_names: List[str], perform_rounding: bool = False) -> None:
        super().__init__(title)
        self.period_names = period_names
        self.students = {}
        self.subject_lists: List[list] = []
        self.perform_rounding = perform_rounding

    def add_subject_list(self, subjects):
        self.subject_lists.append(subjects)

    def get_graph_values(self) -> List[GraphValue]:
        max_size = -1
        for subject_list in self.subject_lists:
            max_size = max(max_size, len(subject_list))

        subjects: List[GraphValue] = [GraphValue(None, [None for _ in range(len(self.period_names))]) for _ in range(max_size)]

        for i, subject_list in enumerate(self.subject_lists):
            for j, subject in enumerate(subject_list):
                subjects[j].label = subject.generic_name
                subjects[j].values[i] = subject.clean_mark

        new_arr = []
        for i, subject in enumerate(subjects.copy()):
            if not subject.values == [None] * len(subject.values):
                new_arr.append(subject)
        return new_arr

    def acquire_axes(self) -> Tuple[str, List[GraphValue]]:
        return (self.period_names, self.get_graph_values())

class PupilSubjectMonthlyAveragesGraph(PupilSubjectAveragesGraph):

    def __init__(self, title: str, period_names: List[str], perform_rounding: bool = False) -> None:
        super().__init__(title, period_names, perform_rounding)
