from __future__ import annotations

import os
import timeit
import traceback

from PyQt5.QtWidgets import QWidget, QFileDialog, QPushButton, QVBoxLayout, QDesktopWidget, QMessageBox, QListWidget, QStackedWidget, QLabel
from typing import List

from graphing import PupilSubjectMonthlyAveragesGraph, ClassPeriodAveragesGraph, ClassMonthlyAveragesGraph
from models import ClassSemesterReportSummary, ClassMonthlyReportSummary, Student
from parsing import PupilSemesterReportParser, PupilMonthlyReportParser, ParsingError
from utils import ConsoleUtils as CU
from settings import Settings

class PupilSelectionWidget(QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Pasirinkite kurį mokinį norite nagrinėti"))
        self.subject_button = QPushButton('Dalykų vidurkiai')
        self.aggregated_button = QPushButton('Bendras vidurkis')
        back_button = QPushButton('Atgal į startą')

        # Disable both buttons by default
        self.disable_buttons()

        # Create a list of student names
        self.name_list = QListWidget()

        selected_graph = None

        def select_name():
            # Not best practise, but bash me all you want
            nonlocal selected_graph
            indexes = self.name_list.selectedIndexes()
            if len(indexes) == 0:
                return
            index = indexes[0].row()
            self.subject_button.setEnabled(True)
            selected_graph = self.graphs[index]

        def display_subject_graph():
            if selected_graph is None:
                return
            selected_graph.display()

        # Bind the events
        self.name_list.itemSelectionChanged.connect(select_name)
        self.subject_button.clicked.connect(display_subject_graph)
        back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(self.name_list)
        layout.addWidget(self.subject_button)
        layout.addWidget(self.aggregated_button)
        layout.addWidget(back_button)

        self.setLayout(layout)

    def disable_buttons(self):
        self.subject_button.setEnabled(False)
        self.aggregated_button.setEnabled(False)

    def populate_list(self, graphs: List[PupilSubjectMonthlyAveragesGraph]):
        self.graphs = graphs
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, graph in enumerate(graphs):
            self.name_list.insertItem(i, graph.title)
        self.disable_buttons()

class App(QWidget):

    MAIN_WIDGET = 0
    SELECT_GRAPH_WIDGET = 1
    SELECT_PUPIL_WIDGET = 2

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.debug = settings.debugging

        self.view_aggregated = False

        self.setWindowTitle('Mokinių pasiekimų analizatorius')

        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480

        self.stack = QStackedWidget()

        # Define generic catch-all button to returning to start
        self.back_button = QPushButton('Atgal į startą')
        self.back_button.clicked.connect(self.go_to_back)

        # Initialize QWidgets
        self.main_widget = QWidget()
        self.select_graph_widget = QWidget()
        self._init_main_widget()
        self._init_select_graph_widget()
        self.select_pupil_widget = PupilSelectionWidget(self)

        # Add said widgets to the StackedWidget
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(self.select_graph_widget)
        self.stack.addWidget(self.select_pupil_widget)

        self.login_widget = QWidget()
        self.select_class_widget = QWidget()
        self.select_timeframe_widget = QWidget()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def _init_main_widget(self):
        layout = QVBoxLayout()
        agg_sem_button = QPushButton('Bendra klasės vidurkių ataskaita pagal trimestrus / pusmečius')
        pup_mon_button = QPushButton('Mokinio dalykų vidurkių ataskaita pagal laikotarpį')
        agg_mon_button = QPushButton('Bendra klasės vidurkių ataskaita pagal laikotarpį')

        agg_sem_button.clicked.connect(self.d_sem_agg)
        pup_mon_button.clicked.connect(self.view_pupil_monthly)
        agg_mon_button.clicked.connect(self.view_aggregated_monthly)

        layout.addWidget(agg_sem_button)
        layout.addWidget(pup_mon_button)
        layout.addWidget(agg_mon_button)
        self.main_widget.setLayout(layout)

    def _init_select_graph_widget(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Pasirinkite kokiu būdų norite pateikti nagrinėjamus duomenis"))
        manual_button = QPushButton('Rankiniu būdų')
        auto_button = QPushButton('Automatiškai iš \'Mano Dienynas\' sistemos')
        auto_button.setEnabled(False)

        manual_button.clicked.connect(self.determine_graph_type)
        layout.addWidget(manual_button)
        layout.addWidget(auto_button)
        layout.addWidget(self.back_button)
        self.select_graph_widget.setLayout(layout)

    def go_to_back(self) -> None:
        self.view_aggregated = False
        self.change_stack(self.MAIN_WIDGET)

    def change_stack(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def view_aggregated_monthly(self):
        self.view_aggregated = True
        self.change_stack(self.SELECT_GRAPH_WIDGET)

    def view_pupil_monthly(self):
        self.view_aggregated = False
        self.change_stack(self.SELECT_GRAPH_WIDGET)

    def determine_graph_type(self):
        summaries = self.request_monthly_summaries()
        if len(summaries) == 0:
            return self.show_error_box("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")

        if self.view_aggregated:
            return self.d_mon_agg(summaries)
        self.d_mon_pup(summaries)

    def initUI(self):
        self.setGeometry(self.left, self.top, self.width, self.height)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.show()

    def request_semester_summaries(self) -> List[ClassSemesterReportSummary]:
        filenames = self.ask_files_dialog()
        summaries: List[ClassSemesterReportSummary] = []
        for filename in filenames:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilSemesterReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                CU.parse_error(base_name, str(e))
                continue
            except Exception as e:
                CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
                if self.debug:
                    print(e)
                    traceback.print_tb(e.__traceback__)
                continue

            if summary.type == "metinis":
                CU.parse_error(base_name, "metinė ataskaita yra nevertinama")
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                CU.parse_error(base_name, "tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            summaries.append(summary)
            CU.default(f"'{base_name}' perskaitytas")
            if self.debug:
                print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

        if len(summaries) == 0:
            CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
        return summaries

    def request_monthly_summaries(self) -> List[ClassMonthlyReportSummary]:
        filenames = self.ask_files_dialog()
        summaries: List[ClassMonthlyReportSummary] = []
        for filename in filenames:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilMonthlyReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                CU.parse_error(base_name, str(e))
                continue
            except Exception as e:
                CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
                if self.debug:
                    print(e)
                    traceback.print_tb(e.__traceback__)
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                CU.parse_error(base_name, "tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            summaries.append(summary)
            CU.default(f"'{base_name}' perskaitytas")
            if self.debug:
                print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

        if len(summaries) == 0:
            CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
        return summaries

    def d_sem_agg(self):
        summaries = self.request_semester_summaries()
        if len(summaries) == 0:
            return self.show_error_box("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")

        # Sort summaries by
        # 1) term start (year)
        # 2) type (semester) (I -> II -> III)
        summaries.sort(key=lambda s: (s.term_start, s.type_as_int))

        # Get the last (the most recent) statistical data and cache student names for later use
        summary = summaries[-1]
        student_cache = [s.name for s in summary.students]

        # Go over each summary and use it to create graph points
        _temp_subject_name_dict = {}
        graph = ClassPeriodAveragesGraph(summary.grade_name + " mokinių vidurkių pokytis", [s.representable_name for s in summaries])
        for i, summary in enumerate(summaries):
            CU.info(f"Nagrinėjamas {summary.period_name} ({summary.term_start}-{summary.term_end})")
            _cached_subs = []
            for student in summary.students:

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    CU.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                subjects = student.get_graphing_subjects()

                # Notify user regarding different generic and original subject names
                # Not in use as of now, but future proofing
                for subject in subjects:
                    if subject.name not in _cached_subs:
                        if subject.name != subject.generic_name:
                            CU.warn(f"Dalykas '{subject.name}' automatiškai pervadintas į '{subject.generic_name}'")
                        _cached_subs.append(subject.name)

                    if _temp_subject_name_dict.get(subject.name, None) is None:
                        _temp_subject_name_dict[subject.name] = (subject.generic_name, summary.grade_name_as_int)

                graph.get_or_create_student(student.name)[i] = student.average

        if self.debug:
            for key in _temp_subject_name_dict.keys():
                name, grade = _temp_subject_name_dict[key]
                print(key, "->", name, f"({grade} kl.)")

        graph.display(
            use_experimental_legend=True
        )

    def d_mon_agg(self, summaries: List[ClassMonthlyReportSummary]):
        # Sort summaries by
        # 1) term start (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))

        # Get the last (the most recent) statistical data and cache student names for later use
        summary = summaries[-1]
        student_cache = [s.name for s in summary.students]

        # Determine graph title
        graph_title = summary.grade_name + " mokinių mėnėsiniai vidurkiai\n"
        if summaries[0].term_start.year == summary.term_start.year:
            graph_title += str(summary.term_start.year)
        else:
            graph_title += f'{summaries[0].term_start.year} - {summary.term_start.year}'

        # Go over each summary and use it to create graph points
        _temp_subject_name_dict = {}
        graph = ClassMonthlyAveragesGraph(graph_title, [s.yearless_representable_name for s in summaries])
        for i, summary in enumerate(summaries):
            CU.info(f"Nagrinėjamas ({summary.term_start}-{summary.term_end})")
            _cached_subs = []
            for student in summary.students:

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    CU.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                subjects = student.get_graphing_subjects()

                # Notify user regarding different generic and original subject names
                # Not in use as of now, but future proofing
                for subject in subjects:
                    if subject.name not in _cached_subs:
                        if subject.name != subject.generic_name:
                            CU.warn(f"Dalykas '{subject.name}' automatiškai pervadintas į '{subject.generic_name}'")
                        _cached_subs.append(subject.name)

                    if _temp_subject_name_dict.get(subject.name, None) is None:
                        _temp_subject_name_dict[subject.name] = (subject.generic_name, summary.grade_name_as_int)

                graph.get_or_create_student(student.name)[i] = student.average

        if self.debug:
            for key in _temp_subject_name_dict.keys():
                name, grade = _temp_subject_name_dict[key]
                print(key, "->", name, f"({grade} kl.)")

        graph.display(
            use_experimental_legend=True
        )
        self.go_to_back()

    def d_mon_pup(self, summaries: List[ClassMonthlyReportSummary]):
        # Sort summaries by
        # 1) term start (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))

        # Get the last (the most recent) statistical data and cache student names for later use
        summary = summaries[-1]
        student_cache = [s.name for s in summaries[-1].students]
        students: List[List[Student]] = [[] for _ in range(len(summaries[-1].students))]

        for summary in summaries:
            CU.info(f"Nagrinėjamas laikotarpis: {summary.representable_name}")
            if self.debug:
                _cached_subs = []
            for j, student in enumerate(summary.students):

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    CU.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                students[j].append(student)

                # Notify user regarding different generic and original subject names
                # Not in use as of now, but future proofing
                if self.debug:
                    for subject in student.get_graphing_subjects():
                        if subject.name not in _cached_subs:
                            if subject.name != subject.generic_name:
                                CU.warn(f"Dalykas '{subject.name}' automatiškai pervadintas į '{subject.generic_name}'")
                            _cached_subs.append(subject.name)

        graphs = []
        for student in students:
            name = student[0].name
            graph = PupilSubjectMonthlyAveragesGraph(name, [s.representable_name for s in summaries])
            for s in student:
                graph.add_subject_list(s.get_graphing_subjects())
            graphs.append(graph)
        self.select_pupil_widget.populate_list(graphs)
        self.change_stack(self.SELECT_PUPIL_WIDGET)

    def show_error_box(self, message: str) -> None:
        """Displays a native error dialog."""
        QMessageBox.critical(self, "Įvyko klaida", message, QMessageBox.Ok, QMessageBox.NoButton)

    def ask_files_dialog(self, caption: str = "Pasirinkite Excel ataskaitų failus") -> List[str]:
        directory = self.settings.last_dir
        if directory is None or not os.path.exists(directory):
            directory = os.path.join(os.environ["userprofile"], "Downloads")

        files, _ = QFileDialog.getOpenFileNames(
            self,
            caption,
            directory,
            "Excel ataskaitų failai (*.xlsx *.xls)"
        )

        # Store the last dir in the settings
        if len(files) > 0:
            self.settings.last_dir = os.path.dirname(files[0])
            self.settings.save()
        return files
