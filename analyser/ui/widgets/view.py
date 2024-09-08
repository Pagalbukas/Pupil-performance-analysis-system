from __future__ import annotations

import logging

from typing import TYPE_CHECKING, List, Optional

from analyser.summaries import ClassPeriodReportSummary, GroupReportSummary, anonymize_pupil_names
from analyser.ui.graphing import (
    ClassPupilAttendanceGraph, ClassPupilAveragesGraph, ClassPupilSubjectGraph
)
from analyser.ui.qt_compat import QtWidgets

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.ui.app import App

class PeriodicViewTypeSelectorWidget(QtWidgets.QWidget): # type: ignore

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summaries: List[ClassPeriodReportSummary] = []

        layout = QtWidgets.QVBoxLayout()
        shared_averages_button = QtWidgets.QPushButton("Bendri klasės vidurkiai")
        shared_attendance_button = QtWidgets.QPushButton("Bendras klasės lankomumas")
        individual_pupil_button = QtWidgets.QPushButton("Individualūs mokinių duomenys")
        return_button = QtWidgets.QPushButton('Grįžti į pradžią')

        shared_averages_button.clicked.connect(self.on_shared_averages_button_click) # type: ignore
        shared_attendance_button.clicked.connect(self.on_shared_attendance_button_click) # type: ignore
        individual_pupil_button.clicked.connect(self.on_individual_pupil_button_click) # type: ignore
        return_button.clicked.connect(self.app.go_to_back) # type: ignore

        layout.addWidget(shared_averages_button) # type: ignore
        layout.addWidget(shared_attendance_button) # type: ignore
        layout.addWidget(individual_pupil_button) # type: ignore
        layout.addWidget(return_button) # type: ignore
        self.setLayout(layout)
        
    def _update_summary_list(self, summaries):
        self.summaries = summaries
        if self.app.settings.hide_names:
            self.summaries = anonymize_pupil_names(self.summaries)
        
    def on_shared_averages_button_click(self):
        self.app.display_period_pupil_averages_graph(self.summaries)
    
    def on_shared_attendance_button_click(self):
        self.app.display_period_attendance_graph(self.summaries)
    
    def on_individual_pupil_button_click(self):
        self.app.open_individual_period_pupil_graph_selector(self.summaries)

class GroupViewTypeSelectorWidget(QtWidgets.QWidget): # type: ignore

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summary: Optional[GroupReportSummary] = None

        layout = QtWidgets.QVBoxLayout()
        shared_averages_button = QtWidgets.QPushButton("Bendri klasės vidurkiai")
        shared_attendance_button = QtWidgets.QPushButton("Bendras klasės lankomumas (greitai...)")
        individual_pupil_button = QtWidgets.QPushButton("Individualūs mokinių duomenys (greitai...)")
        return_button = QtWidgets.QPushButton('Grįžti į pradžią')

        shared_averages_button.clicked.connect(self.on_shared_averages_button_click) # type: ignore
        # TODO: implement
        #shared_attendance_button.clicked.connect(self.on_shared_attendance_button_click) # type: ignore
        #individual_pupil_button.clicked.connect(self.on_individual_pupil_button_click) # type: ignore
        return_button.clicked.connect(self.app.go_to_back) # type: ignore
        
        shared_attendance_button.setEnabled(False)
        individual_pupil_button.setEnabled(False)

        layout.addWidget(shared_averages_button) # type: ignore
        layout.addWidget(shared_attendance_button) # type: ignore
        layout.addWidget(individual_pupil_button) # type: ignore
        layout.addWidget(return_button) # type: ignore
        self.setLayout(layout)

    def _update_summary_list(self, summary: GroupReportSummary):
        self.summary = summary
        if self.app.settings.hide_names:
            self.summary = anonymize_pupil_names([self.summary])[0]
        
    def on_shared_averages_button_click(self):
        assert self.summary is not None
        self.app.display_group_pupil_marks_graph(self.summary)
    
    # TODO: implement
    """def on_shared_attendance_button_click(self):
        assert self.summary is not None
        self.app.display_period_attendance_graph(self.summary)
    
    def on_individual_pupil_button_click(self):
        assert self.summary is not None
        self.app.open_individual_group_pupil_graph_selector(self.summary)
        """

class ClassPupilSelectionWidget(QtWidgets.QWidget): # type: ignore

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summaries: List[ClassPeriodReportSummary] = []
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite, kurį mokinį iš sąrašo norite nagrinėti.")
        self.name_list = QtWidgets.QListWidget()
        self.subject_button = QtWidgets.QPushButton('Dalykų vidurkiai')
        self.attendance_button = QtWidgets.QPushButton('Lankomumas')
        self.averages_button = QtWidgets.QPushButton('Bendras vidurkis')
        back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        def select_name() -> None:
            # Not best practise, but bash me all you want
            indexes = self.name_list.selectedIndexes()
            if len(indexes) == 0:
                return
            index = indexes[0].row() # type: ignore
            self.subject_button.setEnabled(True)
            self.attendance_button.setEnabled(True)
            self.averages_button.setEnabled(True)
            self.selected_index = index

        # Bind the events
        self.name_list.itemSelectionChanged.connect(select_name) # type: ignore
        self.subject_button.clicked.connect(self.display_subject_graph) # type: ignore
        self.attendance_button.clicked.connect(self.display_attendance_graph) # type: ignore
        self.averages_button.clicked.connect(self.display_averages_graph) # type: ignore
        back_button.clicked.connect(self.app.go_to_back) # type: ignore

        layout.addWidget(label)
        layout.addWidget(self.name_list)
        layout.addWidget(self.subject_button)
        layout.addWidget(self.attendance_button)
        layout.addWidget(self.averages_button)
        layout.addWidget(back_button)
        self.setLayout(layout)

    def disable_buttons(self) -> None:
        """Disables per-subject or aggregated graph buttons."""
        self.subject_button.setEnabled(False)
        self.attendance_button.setEnabled(False)
        self.averages_button.setEnabled(False)

    def resolve_pupil_name(self) -> str:
        assert self.selected_index is not None
        return self.summaries[-1].pupils[self.selected_index].name
    
    def display_subject_graph(self) -> None:
        if self.selected_index is None:
            return
        self.app._display_graph(
            ClassPupilSubjectGraph(self.app, self.resolve_pupil_name(), self.summaries)
        )

    def display_attendance_graph(self) -> None:
        if self.selected_index is None:
            return
        self.app._display_graph(
            ClassPupilAttendanceGraph(self.app, self.resolve_pupil_name(), self.summaries)
        )

    def display_averages_graph(self) -> None:
        if self.selected_index is None:
            return
        self.app._display_graph(
            ClassPupilAveragesGraph(self.app, self.resolve_pupil_name(), self.summaries)
        )

    def update_data(self, summaries: List[ClassPeriodReportSummary]) -> None:
        """Updates widget data."""
        self.summaries = summaries
        if self.app.settings.hide_names:
            self.summaries = anonymize_pupil_names(self.summaries)
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, name in enumerate([p.name for p in summaries[-1].pupils]):
            self.name_list.insertItem(i, name)
        self.disable_buttons()

class GroupPupilSelectionWidget(QtWidgets.QWidget): # type: ignore

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summary: Optional[GroupReportSummary] = None
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite, kurį mokinį iš sąrašo norite nagrinėti.")
        self.name_list = QtWidgets.QListWidget()
        self.marks_button = QtWidgets.QPushButton('Pažymiai')
        self.attendance_button = QtWidgets.QPushButton('Lankomumas')
        self.averages_button = QtWidgets.QPushButton('Bendras dalyko vidurkis')
        back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        def select_name() -> None:
            # Not best practise, but bash me all you want
            indexes = self.name_list.selectedIndexes()
            if len(indexes) == 0:
                return
            index = indexes[0].row() # type: ignore
            self.marks_button.setEnabled(True)
            self.attendance_button.setEnabled(True)
            self.averages_button.setEnabled(True)
            self.selected_index = index

        # Bind the events
        self.name_list.itemSelectionChanged.connect(select_name) # type: ignore
        # TODO: implement
        #self.marks_button.clicked.connect(self.display_subject_graph)
        #self.attendance_button.clicked.connect(self.display_attendance_graph)
        #self.averages_button.clicked.connect(self.display_averages_graph)
        back_button.clicked.connect(self.app.go_to_back) # type: ignore

        layout.addWidget(label)
        layout.addWidget(self.name_list)
        layout.addWidget(self.marks_button)
        layout.addWidget(self.attendance_button)
        layout.addWidget(self.averages_button)
        layout.addWidget(back_button)
        self.setLayout(layout)

    def disable_buttons(self) -> None:
        """Disables per-subject or aggregated graph buttons."""
        self.marks_button.setEnabled(False)
        self.attendance_button.setEnabled(False)
        self.averages_button.setEnabled(False)

    def resolve_pupil_name(self) -> str:
        assert self.selected_index is not None
        assert self.summary is not None
        return self.summary.pupils[self.selected_index].name
    
    # TODO: implement
    """def display_subject_graph(self) -> None:
        if self.selected_index is None:
            return
        assert self.summary is not None
        self.app._display_graph(
            ClassPupilSubjectGraph(self.app, self.resolve_pupil_name(), self.summary)
        )

    def display_attendance_graph(self) -> None:
        if self.selected_index is None:
            return
        assert self.summary is not None
        self.app._display_graph(
            ClassPupilAttendanceGraph(self.app, self.resolve_pupil_name(), self.summary)
        )

    def display_averages_graph(self) -> None:
        if self.selected_index is None:
            return
        assert self.summary is not None
        self.app._display_graph(
            ClassPupilAveragesGraph(self.app, self.resolve_pupil_name(), self.summary)
        )
    """

    def update_data(self, summary: GroupReportSummary) -> None:
        """Updates widget data."""
        self.summary = summary
        if self.app.settings.hide_names:
            self.summary = anonymize_pupil_names([self.summary])[0]
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, name in enumerate([p.name for p in summary.pupils]):
            self.name_list.insertItem(i, name)
        self.disable_buttons()
