from __future__ import annotations

import os
import timeit
import logging

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QMessageBox, QFileDialog,
    QWidget, QStackedWidget, QListWidget,
    QLabel, QPushButton,
    QLineEdit
)
from PySide6.QtGui import QScreen
from PySide6.QtCore import QThread, QObject, Signal, Slot
from typing import List

from graphing import PupilSubjectMonthlyAveragesGraph, ClassPeriodAveragesGraph, ClassMonthlyAveragesGraph
from mano_dienynas.client import Client
from models import ClassSemesterReportSummary, ClassMonthlyReportSummary, Student
from parsing import PupilSemesterReportParser, PupilMonthlyReportParser, ParsingError
from settings import Settings

logger = logging.getLogger("analizatorius")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(name)s:%(levelname)s]: %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)


class LoginTaskWorker(QObject):
    success = Signal()
    error = Signal(str)

    def __init__(self, app: App, username: str, password: str) -> None:
        super().__init__()
        self.app = app
        self.username = username
        self.password = password

    @Slot()
    def login(self):
        if self.app.client.is_logged_in:
            return self.error.emit("Vartotojas jau prisijungęs, pala, ką?")

        logged_in = self.app.client.login(self.username, self.password)
        if not logged_in:
            return self.error.emit("Prisijungimas nepavyko, patikrinkite ar suvesti teisingi duomenys")

        # Save the username since login was successful
        self.app.settings.username = self.username
        self.app.settings.save()

        # Obtain filtered roles while at it and verify that user has the rights
        roles = self.app.client.get_filtered_user_roles()
        if len(roles) == 0:
            self.app.client.logout()
            return self.error.emit("Paskyra neturi reikiamų vartotojo teisių. Kol kas palaikomos tik paskyros su 'Klasės vadovas' ir 'Sistemos administratorius' tipais.")

        # Figure out this
        """
        selected_role = [r for r in roles if r.classes is not None][0]
        selected_role.change_role()

        self.app.client.generate_class_monthly_averages_report(selected_role.get_class_id())
        """

        print("Prisijungimas pavyko")
        self.success.emit()

class MainWidget(QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QVBoxLayout()
        agg_sem_button = QPushButton('Bendra klasės vidurkių ataskaita pagal trimestrus / pusmečius')
        pup_mon_button = QPushButton('Mokinio dalykų vidurkių ataskaita pagal laikotarpį')
        agg_mon_button = QPushButton('Bendra klasės vidurkių ataskaita pagal laikotarpį')

        agg_sem_button.clicked.connect(self.app.d_sem_agg)
        pup_mon_button.clicked.connect(self.app.view_pupil_monthly)
        agg_mon_button.clicked.connect(self.app.view_aggregated_monthly)

        layout.addWidget(agg_sem_button)
        layout.addWidget(pup_mon_button)
        layout.addWidget(agg_mon_button)
        self.setLayout(layout)

class SelectGraphWidget(QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QVBoxLayout()
        self.label = QLabel("Pasirinkite kokiu būdų norite pateikti nagrinėjamus duomenis")
        manual_button = QPushButton('Rankiniu būdų')
        auto_button = QPushButton('Automatiškai iš \'Mano Dienynas\' sistemos')
        back_button = QPushButton('Grįžti į pradžią')

        def auto():
            if self.app.client.is_logged_in:
                print("Asking for select class widget, not yet implemented")
                return self.app.change_stack(self.app.SELECT_CLASS_WIDGET)
            self.app.login_widget.clear_fields()
            self.app.login_widget.fill_fields()
            self.app.change_stack(self.app.LOGIN_WIDGET)

        manual_button.clicked.connect(self.app.determine_graph_type)
        auto_button.clicked.connect(auto)
        back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(self.label)
        layout.addWidget(manual_button)
        layout.addWidget(auto_button)
        layout.addWidget(back_button)
        self.setLayout(layout)

    def set_text(self, text: str) -> str:
        self.label.setText(text)

class PupilSelectionWidget(QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        selected_graph = None

        layout = QVBoxLayout()
        label = QLabel("Pasirinkite kurį mokinį norite nagrinėti")
        self.name_list = QListWidget()
        self.subject_button = QPushButton('Dalykų vidurkiai')
        self.aggregated_button = QPushButton('Bendras vidurkis')
        back_button = QPushButton('Grįžti į pradžią')

        def select_name() -> None:
            # Not best practise, but bash me all you want
            nonlocal selected_graph
            indexes = self.name_list.selectedIndexes()
            if len(indexes) == 0:
                return
            index = indexes[0].row()
            self.subject_button.setEnabled(True)
            selected_graph = self.graphs[index]

        def display_subject_graph() -> None:
            if selected_graph is None:
                return
            selected_graph.display()

        # Bind the events
        self.name_list.itemSelectionChanged.connect(select_name)
        self.subject_button.clicked.connect(display_subject_graph)
        back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.name_list)
        layout.addWidget(self.subject_button)
        layout.addWidget(self.aggregated_button)
        layout.addWidget(back_button)
        self.setLayout(layout)

    def disable_buttons(self) -> None:
        """Disables per-subject or aggregated graph buttons."""
        self.subject_button.setEnabled(False)
        self.aggregated_button.setEnabled(False)

    def populate_list(self, graphs: List[PupilSubjectMonthlyAveragesGraph]) -> None:
        """Populates the name list."""
        self.graphs = graphs
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, graph in enumerate(graphs):
            self.name_list.insertItem(i, graph.title)
        self.disable_buttons()

class LoginWidget(QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QVBoxLayout()
        label = QLabel("Prisijungkite prie 'Mano Dienynas' sistemos")
        self.username_field = QLineEdit()
        self.username_field.setPlaceholderText("Jūsų el. paštas")
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Slaptažodis")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton('Prisijungti')
        self.back_button = QPushButton('Grįžti į pradžią')

        self.login_button.clicked.connect(self.login)
        self.back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.username_field)
        layout.addWidget(self.password_field)
        layout.addWidget(self.login_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def fill_fields(self) -> None:
        """Fills the input fields with default and saved values."""
        self.username_field.setText(self.app.settings.username)

    def clear_fields(self) -> None:
        """Clears password and username fields."""
        self.username_field.clear()
        self.password_field.clear()

    def enable_gui(self) -> None:
        """Enables GUI components."""
        self.username_field.setEnabled(True)
        self.password_field.setEnabled(True)
        self.login_button.setEnabled(True)
        self.back_button.setEnabled(True)

    def disable_gui(self) -> None:
        """Disables GUI components."""
        self.username_field.setEnabled(False)
        self.password_field.setEnabled(False)
        self.login_button.setEnabled(False)
        self.login_button.clearFocus()
        self.back_button.setEnabled(False)

    def propagate_error(self, error_msg: str) -> None:
        """Display an error and re-enable the GUI."""
        self.enable_gui()
        self.app.show_error_box(error_msg)

    def on_error_signal(self, error: str) -> None:
        """Callback of LoginTaskWorker thread on error."""
        self.propagate_error(error)
        self.login_thread.quit()

    def on_success_signal(self) -> None:
        """Callback of LoginTaskWorker thread on success."""
        self.login_thread.quit()
        self.app.change_stack(self.app.SELECT_CLASS_WIDGET)

    def login(self) -> None:
        """Attempt to log into Mano Dienynas.

        Starts a LoginTask worker thread."""
        username = self.username_field.text()
        password = self.password_field.text()

        if username.strip() == "" or password.strip() == "":
            return self.propagate_error("Įveskite prisijungimo duomenis")

        self.disable_gui()
        self.login_worker = LoginTaskWorker(self.app, username, password)
        self.login_thread = QThread()
        self.login_worker.moveToThread(self.login_thread)

        # Connect signals
        self.login_worker.error.connect(self.on_error_signal)
        self.login_worker.success.connect(self.on_success_signal)
        self.login_thread.started.connect(self.login_worker.login)

        self.login_thread.start()

class App(QWidget):

    MAIN_WIDGET = 0
    SELECT_GRAPH_WIDGET = 1
    SELECT_PUPIL_WIDGET = 2
    LOGIN_WIDGET = 3
    SELECT_CLASS_WIDGET = 4

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.debug = settings.debugging
        self.client = Client()

        if self.debug:
            logger.setLevel(logging.DEBUG)
            ch.setLevel(logging.DEBUG)

        self.view_aggregated = False

        self.setWindowTitle('Mokinių pasiekimų analizatorius')

        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480

        self.stack = QStackedWidget()

        # Initialize QWidgets
        self.main_widget = MainWidget(self)
        self.select_graph_widget = SelectGraphWidget(self)
        self.select_pupil_widget = PupilSelectionWidget(self)
        self.login_widget = LoginWidget(self)

        # Add said widgets to the StackedWidget
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(self.select_graph_widget)
        self.stack.addWidget(self.select_pupil_widget)
        self.stack.addWidget(self.login_widget)

        self.select_class_widget = QWidget()
        self.select_timeframe_widget = QWidget()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def go_to_back(self) -> None:
        """Return to the main widget."""
        self.view_aggregated = False
        self.change_stack(self.MAIN_WIDGET)

    def change_stack(self, index: int) -> None:
        """Change current stack widget."""
        self.stack.setCurrentIndex(index)

    def view_aggregated_monthly(self):
        self.view_aggregated = True
        self.change_stack(self.SELECT_GRAPH_WIDGET)

    def view_pupil_monthly(self):
        self.view_aggregated = False
        self.change_stack(self.SELECT_GRAPH_WIDGET)

    def determine_graph_type(self):
        filenames = self.ask_files_dialog()
        if len(filenames) == 0:
            return

        summaries = self.generate_monthly_summaries(filenames)
        if len(summaries) == 0:
            return self.show_error_box("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")

        # Sort summaries by term start, ascending (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))
        if self.view_aggregated:
            return self.d_mon_agg(summaries)
        self.d_mon_pup(summaries)

    def initUI(self):
        self.setGeometry(self.left, self.top, self.width, self.height)
        center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        self.move(geo.topLeft())
        self.show()

    def generate_semester_summaries(self, files: List[str]) -> List[ClassSemesterReportSummary]:
        """Generates a list of semester type summaries."""
        summaries: List[ClassSemesterReportSummary] = []
        for filename in files:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilSemesterReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                logger.error(f"{base_name}: {e}")
                continue
            except Exception as e:
                logger.exception(f"{base_name}: {e}")
                continue

            if summary.type == "metinis":
                logger.warn(f"{base_name}: metinė ataskaita yra nevertinama")
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                logger.warn(f"{base_name}: tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
            summaries.append(summary)

        if len(summaries) == 0:
            logger.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
        return summaries

    def generate_monthly_summaries(self, files: List[str]) -> List[ClassMonthlyReportSummary]:
        """Generates a list of monthly summaries."""
        summaries: List[ClassMonthlyReportSummary] = []
        for filename in files:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilMonthlyReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                logger.error(f"{base_name}: {e}")
                continue
            except Exception as e:
                logger.exception(f"{base_name}: {e}")
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                logger.warn(f"{base_name}: tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
            summaries.append(summary)

        if len(summaries) == 0:
            logger.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
        return summaries

    def d_sem_agg(self):
        files = self.ask_files_dialog()
        if len(files) == 0:
            return

        summaries = self.generate_semester_summaries(files)
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
        graph = ClassPeriodAveragesGraph(summary.grade_name + " mokinių bendrų vidurkių pokytis", [s.representable_name for s in summaries])
        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas {summary.period_name} ({summary.term_start}-{summary.term_end})")
            for student in summary.students:

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    logger.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                graph.get_or_create_student(student.name)[i] = student.average

        graph.display(use_experimental_legend=True)

    def d_mon_agg(self, summaries: List[ClassMonthlyReportSummary]):
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
        graph = ClassMonthlyAveragesGraph(graph_title, [s.yearless_representable_name for s in summaries])
        for i, summary in enumerate(summaries):
            logger.info(f"Nagrinėjamas ({summary.term_start}-{summary.term_end})")
            for student in summary.students:

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    logger.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                graph.get_or_create_student(student.name)[i] = student.average

        graph.display(use_experimental_legend=True)
        self.go_to_back()

    def d_mon_pup(self, summaries: List[ClassMonthlyReportSummary]):

        # Get the last (the most recent) statistical data and cache student names for later use
        summary = summaries[-1]
        student_cache = [s.name for s in summary.students]
        students: List[List[Student]] = [[] for _ in range(len(summary.students))]

        for summary in summaries:
            logger.info(f"Nagrinėjamas laikotarpis: {summary.representable_name}")
            for j, student in enumerate(summary.students):

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    logger.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                students[j].append(student)

        graphs = []
        for student in students:
            name = student[0].name
            graph = PupilSubjectMonthlyAveragesGraph(name, [s.representable_name for s in summaries])
            for s in student:
                graph.add_subject_list(s.get_graphing_subjects())
            graphs.append(graph)
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.populate_list(graphs)
        self.change_stack(self.SELECT_PUPIL_WIDGET)

    def show_error_box(self, message: str) -> None:
        """Displays a native error dialog."""
        QMessageBox.critical(self, "Įvyko klaida", message, QMessageBox.Ok, QMessageBox.NoButton)

    def ask_files_dialog(self, caption: str = "Pasirinkite Excel ataskaitų failus") -> List[str]:
        """Displays a file selection dialog for picking Excel files."""
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
