from __future__ import annotations

import logging

from typing import TYPE_CHECKING, List, Optional

from analyser.graphing import (
    PupilPeriodicAttendanceGraph, PupilPeriodicAveragesGraph, PupilSubjectPeriodicAveragesGraph
)
from analyser.summaries import ClassPeriodReportSummary
from analyser.qt_compat import QtWidgets

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

class PeriodicViewTypeSelectorWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summaries = []

        layout = QtWidgets.QVBoxLayout()
        shared_averages_button = QtWidgets.QPushButton("Bendri klasės vidurkiai")
        shared_attendance_button = QtWidgets.QPushButton("Bendras klasės lankomumas")
        individual_pupil_button = QtWidgets.QPushButton("Individualūs mokinių duomenys")
        return_button = QtWidgets.QPushButton('Grįžti į pradžią')

        shared_averages_button.clicked.connect(self.on_shared_averages_button_click)
        shared_attendance_button.clicked.connect(self.on_shared_attendance_button_click)
        individual_pupil_button.clicked.connect(self.on_individual_pupil_button_click)
        return_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(shared_averages_button) # type: ignore
        layout.addWidget(shared_attendance_button) # type: ignore
        layout.addWidget(individual_pupil_button) # type: ignore
        layout.addWidget(return_button) # type: ignore
        self.setLayout(layout)
        
    def _update_summary_list(self, summaries):
        self.summaries = summaries
        
    def on_shared_averages_button_click(self):
        self.app.display_period_pupil_averages_graph(self.summaries)
    
    def on_shared_attendance_button_click(self):
        self.app.display_period_attendance_graph(self.summaries)
    
    def on_individual_pupil_button_click(self):
        self.app.open_individual_period_pupil_graph_selector(self.summaries)

class GroupViewTypeSelectorWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.summaries = []

        layout = QtWidgets.QVBoxLayout()
        shared_averages_button = QtWidgets.QPushButton("Bendri klasės vidurkiai")
        shared_attendance_button = QtWidgets.QPushButton("Bendras klasės lankomumas (greitai...)")
        individual_pupil_button = QtWidgets.QPushButton("Individualūs mokinių duomenys (greitai...)")
        return_button = QtWidgets.QPushButton('Grįžti į pradžią')

        shared_averages_button.clicked.connect(self.on_shared_averages_button_click)
        shared_attendance_button.clicked.connect(self.on_shared_attendance_button_click)
        individual_pupil_button.clicked.connect(self.on_individual_pupil_button_click)
        return_button.clicked.connect(self.app.go_to_back)
        
        shared_attendance_button.setEnabled(False)
        individual_pupil_button.setEnabled(False)

        layout.addWidget(shared_averages_button) # type: ignore
        layout.addWidget(shared_attendance_button) # type: ignore
        layout.addWidget(individual_pupil_button) # type: ignore
        layout.addWidget(return_button) # type: ignore
        self.setLayout(layout)

    def _update_summary_list(self, summaries):
        self.summaries = summaries
        
    def on_shared_averages_button_click(self):
        self.app.display_group_pupil_marks_graph(self.summaries)
    
    def on_shared_attendance_button_click(self):
        self.app.display_period_attendance_graph(self.summaries)
    
    def on_individual_pupil_button_click(self):
        self.app.open_individual_group_pupil_graph_selector(self.summaries)

class PupilSelectionWidget(QtWidgets.QWidget):

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
        self.name_list.itemSelectionChanged.connect(select_name)
        self.subject_button.clicked.connect(self.display_subject_graph)
        self.attendance_button.clicked.connect(self.display_attendance_graph)
        self.averages_button.clicked.connect(self.display_averages_graph)
        back_button.clicked.connect(self.app.go_to_back)

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
            PupilSubjectPeriodicAveragesGraph(self.app, self.summaries, self.resolve_pupil_name())
        )

    def display_attendance_graph(self) -> None:
        if self.selected_index is None:
            return
        self.app._display_graph(
            PupilPeriodicAttendanceGraph(self.app, self.summaries, self.resolve_pupil_name())
        )

    def display_averages_graph(self) -> None:
        if self.selected_index is None:
            return
        self.app._display_graph(
            PupilPeriodicAveragesGraph(self.app, self.summaries, self.resolve_pupil_name())
        )

    def update_data(self, summaries: List[ClassPeriodReportSummary]) -> None:
        """Updates widget data."""
        self.summaries = summaries
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, name in enumerate([p.name for p in summaries[-1].pupils]):
            self.name_list.insertItem(i, name)
        self.disable_buttons()

