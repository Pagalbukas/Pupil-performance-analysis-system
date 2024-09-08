from __future__ import annotations
from abc import ABC, abstractmethod

import datetime
import logging
import math

from typing import (
    TYPE_CHECKING,
    Any, Dict, List,
    Optional, Tuple,
    TypeVar, Union
)

from analyser.errors import GraphingError
from analyser.summaries import AnySummary, ClassReportSummary, GroupReportSummary # type: ignore

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
    from analyser.summaries import ClassPeriodReportSummary, ClassSemesterReportSummary

def _get_year_field(term_start: datetime.datetime, term_end: datetime.datetime) -> str:
    """Returns year field for the specified datetime."""
    if term_start.year == term_end.year:
        return f"{term_start.year} m."
    return f"{term_start.year} – {term_end.year} m."

class GraphValue:

    def __init__(self, label: str, values: Any) -> None:
        self.label = label
        self.values = values

    def __repr__(self) -> str:
        return f'<GraphValue label=\'{self.label}\' values={self.values}>'

class BaseGraph:

    LINE_STYLES = ['-', '--', '-.', ':']
    STYLE_COUNT = len(LINE_STYLES)

    def __init__(self, app: App) -> None:
        self.app = app
        self._title: Optional[str] = None
        self._x: List[str] = []
        self._y: List[GraphValue] = []

    @property
    def title(self) -> str:
        """Represents graph title."""
        return self._title or "Grafikas"

    @property
    def window_title(self) -> str:
        """Represents window title."""
        return self.title.replace("\n", " ").replace(":", "_")
    
    @property
    def axis_labels(self) -> Tuple[str, str]:
        """Represents graph x and y value labels."""
        return "Laikotarpis", "Vidurkis"

    def set_graph_title(self, title: str) -> None:
        """Sets the title of the graph."""
        self._title = title

    def acquire_axes(self) -> Tuple[List[str], List[GraphValue]]:
        return self._x, self._y

    def display(
        self
    ) -> None:
        """Instructs matplotlib to display a graph."""
        self.app.matplotlib_window.load_from_graph(self)
        return self.app.matplotlib_window.show()

class SingleSummaryGraph(ABC):
    pass

class MultiSummaryGraph(ABC):
    pass

class ClassGraph(MultiSummaryGraph, BaseGraph):
    
    def __init__(self, app: App) -> None:
        super().__init__(app)

class GroupGraph(SingleSummaryGraph, BaseGraph):
    
    def __init__(self, app: App) -> None:
        super().__init__(app)
        
    def _get_month_name(self, month: int) -> str:
        """Returns string of the month's name."""
        return MONTH_NAMES.get(month, str(month))
        
class GroupAveragesGraph(GroupGraph):
    
    def __init__(self, app: App, summary: GroupReportSummary) -> None:
        super().__init__(app)
        self.parse_summary(summary)
    
    @property
    def axis_labels(self) -> Tuple[str, str]:
        return "Mėnesis", "Vidurkis"
    
    def _resolve_graph_title(self, summary: GroupReportSummary) -> str:
        group_name = summary.group_name
        title = f'Grupė: {group_name}\nVidurkiai\n'
        title += _get_year_field(summary.term_start, summary.term_end)
        return title
    
    def parse_summary(self, summary: GroupReportSummary) -> None:
        self.set_graph_title(self._resolve_graph_title(summary))

        logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
        
        # Parse available months and store them in a list
        months: List[int] = []
        dates = [m.date for m in summary.pupils[0].marks if m.date is not None]
        for date in dates:
            if date.month in months:
                continue
            months.append(date.month)

        data: Dict[str, List[Union[int, float, None]]] = {}
        for pupil in summary.pupils:
            # Initialize pupil entries in a dict
            data[pupil.name] = [None for _ in range(len(months))]
            for i, month in enumerate(months):
                marks = pupil.get_valid_marks_for_month(month)
                if len(marks) == 0:
                    continue
                mark_sum = sum([m.clean for m in marks if isinstance(m.clean, int) or isinstance(m.clean, float)])
                for mark in marks:
                    if mark.clean is None:
                        continue
                data[pupil.name][i] = round(mark_sum / len(marks), 2)
        
        # Save data
        self._x = [self._get_month_name(m) for m in months]
        self._y = [GraphValue(p.name, data[p.name]) for p in summary.pupils]

class ClassAveragesGraph(ClassGraph):
    """A unified aggregated class averages graph."""

    def __init__(
        self,
        app: App,
        summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]
    ) -> None:
        super().__init__(app)
        self.parse_summaries(summaries)

    def _resolve_graph_title(self, summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]) -> str:
        title = f'Klasė: {summaries[-1].grade_name}\nBendri mokinių vidurkiai\n'
        title += _get_year_field(summaries[0].term_start, summaries[-1].term_end)
        return title

    @property
    def window_title(self) -> str:
        return "Bendri klasės mokinių vidurkiai"
    
    def parse_summaries(self, summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]) -> None:
        self.set_graph_title(self._resolve_graph_title(summaries))
        
        pupil_names = [s.name for s in summaries[-1].pupils]
        period_names = [s.representable_name for s in summaries]
        pupils: Dict[str, List[Union[int, float, None]]] = {}

        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
            for pupil in summary.pupils:
                # If student name is not in cache, ignore them
                if pupil.name not in pupil_names:
                    logger.warn(f"Mokinys '{pupil.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                if pupils.get(pupil.name) is None:
                    pupils[pupil.name] = [None for _ in range(len(period_names))]
                pupils[pupil.name][i] = pupil.average.clean
                    
        self._x = period_names
        self._y = [GraphValue(n, pupils[n]) for n in pupils.keys()]

class ClassAttendanceGraph(ClassGraph):
    """A unified aggregated class averages graph."""

    def __init__(
        self,
        app: App,
        summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]
    ) -> None:
        super().__init__(app)
        self.parse_summaries(summaries)

    def _resolve_graph_title(self, summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]) -> str:
        title = f'Klasė: {summaries[-1].grade_name}\nPraleistų pamokų kiekis\n'
        title += _get_year_field(summaries[0].term_start, summaries[-1].term_end)
        return title

    @property
    def window_title(self) -> str:
        return "Bendras klasės lankomumas"
    
    @property
    def axis_labels(self) -> Tuple[str, str]:
        return "Laikotarpis", "Praleistų pamokų kiekis"

    def parse_summaries(self, summaries: Union[List[ClassSemesterReportSummary], List[ClassPeriodReportSummary]]) -> None:
        self.set_graph_title(self._resolve_graph_title(summaries))
        
        pupil_names = [s.name for s in summaries[-1].pupils]
        period_names = [s.representable_name for s in summaries]
        pupils: Dict[str, List[Optional[int]]] = {}

        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
            for pupil in summary.pupils:
                # If student name is not in cache, ignore them
                if pupil.name not in pupil_names:
                    logger.warn(f"Mokinys '{pupil.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                if pupils.get(pupil.name) is None:
                    pupils[pupil.name] = [None for _ in range(len(period_names))]
                pupils[pupil.name][i] = pupil.attendance.total_missed
                    
        self._x = period_names
        self._y = [GraphValue(n, pupils[n]) for n in pupils.keys()]

class ClassPupilGraph(ClassGraph):

    def __init__(self, app: App, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        super().__init__(app)
        
        # Some data sanitization
        pupils = [p for p in summaries[-1].pupils if p.name == pupil_name]
        if len(pupils) == 0:
            raise GraphingError("Mokinys nurodytų vardu neegzistuoja?")
        if len(pupils) > 1:
            raise GraphingError("Yra 2 ar daugiau mokinių tokiu pat vardu!")

class ClassPupilAveragesGraph(ClassPupilGraph):

    def __init__(self, app: App, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        super().__init__(app, pupil_name, summaries)
        self.parse_summaries(pupil_name, summaries)
    
    @property
    def window_title(self) -> str:
        return "Mokinio bendras vidurkis"
    
    def _resolve_graph_title(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> str:
        title = f'Mokinys: {pupil_name}\nBendras vidurkis\n'
        title += _get_year_field(summaries[0].term_start, summaries[-1].term_end)
        return title
    
    def parse_summaries(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        self.set_graph_title(self._resolve_graph_title(pupil_name, summaries))
        
        # Initialize temporary variables
        averages: Dict[str, List[Union[int, float, None]]] = {}
        period_names = [s.representable_name for s in summaries]
        
        # Obtain student averages
        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
            for pupil in summary.pupils:
                if averages.get(pupil.name) is None:
                    averages[pupil.name] = [None for _ in range(len(period_names))]
                averages[pupil.name][i] = pupil.average.clean
        
        # Obtain class average information
        class_averages: List[Tuple[Union[int, float], float]] = [(0, 0) for _ in range(len(period_names))]
        for values in averages.values():
            for i, average in enumerate(values):
                if average is not None:
                    x, y = class_averages[i]
                    class_averages[i] = (x + average, y + 1)

        # Calculate class averages
        try:
            calculated_averages = [round(s / t, 2) for s, t in class_averages]
        except ZeroDivisionError:
            raise GraphingError("Klasė neturi jokių pažymių, kad būtų galima piešti grafiką!")
        
        # Save said data
        self._x = period_names
        self._y = [
            GraphValue("Mokinio vidurkis", averages[pupil_name]),
            GraphValue("Klasės vidurkis", calculated_averages)
        ]

class ClassPupilAttendanceGraph(ClassPupilGraph):

    def __init__(self, app: App, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        super().__init__(app, pupil_name, summaries)
        self.parse_summaries(pupil_name, summaries)
    
    @property
    def window_title(self) -> str:
        return "Mokinio lankomumas"
    
    def _resolve_graph_title(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> str:
        title = f'Mokinys: {pupil_name}\nPraleistų pamokų kiekis\n'
        title += _get_year_field(summaries[0].term_start, summaries[-1].term_end)
        return title
    
    def parse_summaries(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        self.set_graph_title(self._resolve_graph_title(pupil_name, summaries))
        
        period_names = [s.representable_name for s in summaries]
        averages: Dict[str, List[Optional[int]]] = {}
        
        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
            for pupil in summary.pupils:
                if averages.get(pupil.name) is None:
                    averages[pupil.name] = [None for _ in range(len(period_names))]
                averages[pupil.name][i] = pupil.attendance.total_missed
        
        def clean_round(raw_float: float) -> Union[float, int]:
            rounded = round(raw_float, 2)
            if str(rounded).split(".")[1] == "0":
                return math.trunc(rounded)
            return rounded
        
        class_averages: List[List[Union[int, float]]] = [[0, 0] for _ in range(len(period_names))]
        for values in averages.values():
            for i, average in enumerate(values):
                if average is not None:
                    class_averages[i][0] += average
                    class_averages[i][1] += 1
        try:
            calculated_averages = [clean_round(s / t) for s, t in class_averages]
        except ZeroDivisionError:
            raise GraphingError("Klasė neturi jokių pažymių, kad būtų galima piešti grafiką!")
        
        self._x = period_names
        self._y = [
            GraphValue("Mokinio kiekis", averages[pupil_name]),
            GraphValue("Klasės vidurkis", calculated_averages)
        ]

class ClassPupilSubjectGraph(ClassPupilGraph):

    def __init__(self, app: App, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        super().__init__(app, pupil_name, summaries)
        self.parse_summaries(pupil_name, summaries)
    
    @property
    def window_title(self) -> str:
        return "Mokinio dalykų vidurkis"
    
    def _resolve_graph_title(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> str:
        title = f'Mokinys: {pupil_name}\nDalykų vidurkiai\n'
        title += _get_year_field(summaries[0].term_start, summaries[-1].term_end)
        return title
    
    def parse_summaries(self, pupil_name: str, summaries: List[ClassPeriodReportSummary]) -> None:
        self.set_graph_title(self._resolve_graph_title(pupil_name, summaries))

        period_names = [s.representable_name for s in summaries]
        subjects: Dict[str, List[Union[int, float, None]]] = {}

        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas laikotarpis: {summary.full_representable_name}")
            pupil = [p for p in summary.pupils if p.name == pupil_name][0]
            for subject in pupil.sorted_subjects:
                if not subject.is_ignored:
                    if subjects.get(subject.name) is None:
                        subjects[subject.name] = [None for _ in range(len(period_names))]
                    subjects[subject.name][i] = subject.mark.clean

        values = []
        for name in subjects:
            marks = subjects[name]
            if marks == [None] * len(marks):
                continue
            values.append(GraphValue(name, marks))
        if len(values) == 0:
            raise GraphingError("Mokinys neturi jokių pažymių, kad būtų galima piešti grafiką!")

        self._x = period_names
        self._y = values

AnyGraph = TypeVar(
    'AnyGraph',
    ClassAveragesGraph, ClassAttendanceGraph,
    ClassPupilSubjectGraph, ClassPupilAttendanceGraph, ClassPupilAveragesGraph,
    GroupAveragesGraph
)
