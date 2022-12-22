from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from analyser.errors import ParsingError
from analyser.qt_compat import QtWidgets
from analyser.parsing import parse_group_summary_file, parse_periodic_summary_files, parse_semester_summary_files

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

class ManualFileSelectorWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QtWidgets.QVBoxLayout()
        semester_button = QtWidgets.QPushButton('Trimestrų/pusmečių ataskaitos (auklėtojams)')
        period_button = QtWidgets.QPushButton('Vidurkių ataskaitos (auklėtojams)')
        group_button = QtWidgets.QPushButton('Grupių ataskaitos (mokytojams)')
        return_button = QtWidgets.QPushButton('Grįžti į pradžią')

        semester_button.clicked.connect(self.on_semester_button_click)
        period_button.clicked.connect(self.on_period_button_click)
        group_button.clicked.connect(self.on_group_button_click)
        return_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(semester_button) # type: ignore
        layout.addWidget(period_button) # type: ignore
        layout.addWidget(group_button) # type: ignore
        layout.addWidget(return_button) # type: ignore
        self.setLayout(layout)
    
    def on_semester_button_click(self) -> None:
        files = self.app.ask_files_dialog()
        if len(files) == 0:
            return

        # Generate summary objects from files
        summaries = parse_semester_summary_files(files)
        if len(summaries) == 0:
            return self.app.show_error_box("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")

        # Sort summaries by
        # 1) term start (year)
        # 2) type (semester) (I -> II -> III)
        summaries.sort(key=lambda s: (s.term_start, s.type_as_int))
        self.app.display_semester_pupil_averages_graph(summaries)

    def on_period_button_click(self) -> None:
        files = self.app.ask_files_dialog()
        if len(files) == 0:
            return

        # Generate summary objects from files
        summaries = parse_periodic_summary_files(files)
        if len(summaries) == 0:
            return self.app.show_error_box("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")

        # Sort summaries by term start, ascending (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))
        
        # Open type selection
        self.app.open_periodic_type_selector(summaries)

    def on_group_button_click(self) -> None:
        file = self.app.ask_file_dialog()
        if file is None:
            return

        # Generate summary objects from files
        try:
            summary = parse_group_summary_file(file)
        except ParsingError as e:
            # return self.app.show_error_box("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
            return self.app.show_error_box(str(e))

        # Open type selection
        self.app.open_group_type_selector(summary)
