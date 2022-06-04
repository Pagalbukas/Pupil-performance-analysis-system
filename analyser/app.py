from __future__ import annotations

import os
import platform
import sys
import timeit
import logging

from logging.handlers import RotatingFileHandler
from typing import List, Optional, Tuple

from analyser.errors import ParsingError
from analyser.files import get_data_dir, get_home_dir, get_log_file, open_path
from analyser.graphing import (
    MatplotlibWindow, PupilPeriodicAttendanceGraph, PupilPeriodicAveragesGraph, PupilSubjectPeriodicAveragesGraph,
    UnifiedClassAveragesGraph, UnifiedClassAttendanceGraph
)
from analyser.mano_dienynas.client import Client, UnifiedAveragesReportGenerator, Class # type: ignore
from analyser.parsing import PupilSemesterReportParser, PupilPeriodicReportParser
from analyser.settings import Settings
from analyser.summaries import ClassSemesterReportSummary, ClassPeriodReportSummary
from analyser.qt_compat import QtWidgets, QtCore, QtGui, Qt

__VERSION__ = (1, 1, 5)
__VERSION_NAME = f"{__VERSION__[0]}.{__VERSION__[1]}.{__VERSION__[2]}"
REPO_URL = "https://mokytojams.svetikas.lt/"

logger = logging.getLogger("analizatorius")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(f'[%(asctime)s %(name)s-{__VERSION_NAME}:%(levelname)s]: %(message)s', "%Y-%m-%d %H:%M:%S")

fh = RotatingFileHandler(get_log_file(), encoding="utf-8", maxBytes=1024 * 512, backupCount=10)
fh.setFormatter(formatter)
fh.setLevel(logging.INFO)
logger.addHandler(fh)

# Detect Nuitka compiled code and do not create a StreamHandler
ch = None
if "__compiled__" not in dir():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class GenerateReportWorker(QtCore.QObject):
    success = QtCore.Signal(list)
    error = QtCore.Signal(str)
    progress = QtCore.Signal(tuple)

    def __init__(self, app: App, class_o: Class) -> None:
        super().__init__()
        self.app = app
        self.class_o = class_o

    @QtCore.Slot() # type: ignore
    def generate_periodic(self):
        try:
            generator = self.app.client.get_class_averages_report_options(self.class_o.id)
            total = generator.expected_period_report_count
            self.progress.emit((total, 0))
            files = []
            for i, file in enumerate(generator.generate_periodic_reports()):
                self.progress.emit((total, i + 1))
                files.append(file)
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))
        self.success.emit(files)

    @QtCore.Slot() # type: ignore
    def generate_monthly(self):
        try:
            generator = self.app.client.get_class_averages_report_options(self.class_o.id)
            total = generator.expected_monthly_report_count
            self.progress.emit((total, 0))
            files = []
            for i, file in enumerate(generator.generate_monthly_reports()):
                self.progress.emit((total, i + 1))
                files.append(file)
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))
        self.success.emit(files)

class ChangeRoleWorker(QtCore.QObject):
    success = QtCore.Signal()
    error = QtCore.Signal(str)

    def __init__(self, app: App, role_index: int) -> None:
        super().__init__()
        self.app = app
        self.index = role_index

    @QtCore.Slot() # type: ignore
    def change_role(self):
        try:
            self.app.client.get_filtered_user_roles()[self.index].change_role()
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))
        self.success.emit()

class LoginTaskWorker(QtCore.QObject):
    success = QtCore.Signal(bool)
    error = QtCore.Signal(str)

    def __init__(self, app: App, username: str, password: str) -> None:
        super().__init__()
        self.app = app
        self.username = username
        self.password = password

    @QtCore.Slot() # type: ignore
    def login(self):
        # Should never be called
        if self.app.client.is_logged_in:
            return self.error.emit("Vartotojas jau prisijungęs, pala, ką?")

        # Do the actual login request
        try:
            logged_in = self.app.client.login(self.username, self.password)
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))

        if not logged_in:
            return self.error.emit("Prisijungimas nepavyko, patikrinkite, ar duomenys suvesti teisingai!")

        # Save the username since login was successful
        self.app.settings.username = self.username
        self.app.settings.save()

        # Obtain filtered roles while at it and verify that user has the rights
        try:
            roles = self.app.client.get_filtered_user_roles()
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))

        if len(roles) == 0:
            self.app.client.logout()
            return self.error.emit(
                "Paskyra neturi reikiamų vartotojo teisių. "
                "Kol kas palaikomos tik paskyros su 'Klasės vadovas' ir 'Sistemos administratorius' tipais."
            )

        if len(roles) == 1:
            if not roles[0].is_active:
                try:
                    roles[0].change_role()
                except Exception as e:
                    logger.exception(e)
                    return self.error.emit(str(e))
            logger.info(f"Paskyros tipas pasirinktas automatiškai į '{roles[0].title}'")
        self.success.emit(len(roles) == 1)


class MainWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QtWidgets.QVBoxLayout()
        agg_sem_button = QtWidgets.QPushButton('Bendra klasės vidurkių ataskaita pagal trimestrus / pusmečius')
        agg_mon_button = QtWidgets.QPushButton('Bendra klasės vidurkių ataskaita pagal laikotarpį')
        att_mon_button = QtWidgets.QPushButton('Bendra klasės lankomumo ataskaita pagal laikotarpį')
        pup_mon_button = QtWidgets.QPushButton('Individualizuota mokinio vidurkių ataskaita pagal laikotarpį')
        settings_button = QtWidgets.QPushButton('Nustatymai')
        notice_label = QtWidgets.QLabel()

        agg_sem_button.clicked.connect(self.app.view_aggregated_semester_graph)
        agg_mon_button.clicked.connect(self.app.view_aggregated_monthly_selector)
        att_mon_button.clicked.connect(self.app.view_attendance_monthly_selector)
        pup_mon_button.clicked.connect(self.app.view_pupil_monthly_selector)
        settings_button.clicked.connect(self.on_settings_button_click)

        major, minor, patch = __VERSION__

        notice_label.setText(f"<a href=\"{REPO_URL}\">v{major}.{minor}.{patch} Dominykas Svetikas © 2022</a>")
        notice_label.setTextFormat(Qt.RichText)
        notice_label.setTextInteractionFlags(Qt.TextBrowserInteraction) # type: ignore
        notice_label.setOpenExternalLinks(True)

        # God forbid I have to mess with this sh*t again
        # Took longer than aligning a div in CSS
        layout.addWidget(agg_sem_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(agg_mon_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(att_mon_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(pup_mon_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(settings_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(notice_label, alignment=Qt.AlignRight | Qt.AlignBottom | Qt.AlignJustify) # type: ignore
        self.setLayout(layout)

    def on_settings_button_click(self) -> None:
        """Reacts to settings button click."""
        self.app.view_settings()


class SelectGraphWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel((
            "Pasirinkite, kokiu būdu norite pateikti nagrinėjamus duomenis.\n\n"
            "Nagrinėjamus duomenis galite pateikti:\n"
            "- pasirenkant vidurkių ataskaitų failus rankiniu būdu;\n"
            "- leidžiant tai automatiškai padaryti programai, kuri surinks reikiamas ataskaitas iš 'Mano Dienynas' sistemos."
        ))
        manual_button = QtWidgets.QPushButton('Rankiniu būdu')
        auto_button = QtWidgets.QPushButton('Automatiškai iš \'Mano Dienynas\' sistemos')
        back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        def auto():
            if self.app.client.is_logged_in:
                if len(self.app.client.get_filtered_user_roles()) == 1:
                    self.app.select_class_widget.update_data()
                    return self.app.change_stack(self.app.SELECT_CLASS_WIDGET)
                return self.app.change_stack(self.app.SELECT_USER_ROLE_WIDGET)
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
        self.aggregated_button = QtWidgets.QPushButton('Bendras vidurkis')
        back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        def select_name() -> None:
            # Not best practise, but bash me all you want
            indexes = self.name_list.selectedIndexes()
            if len(indexes) == 0:
                return
            index = indexes[0].row() # type: ignore
            self.subject_button.setEnabled(True)
            self.attendance_button.setEnabled(True)
            self.aggregated_button.setEnabled(True)
            self.selected_index = index

        # Bind the events
        self.name_list.itemSelectionChanged.connect(select_name)
        self.subject_button.clicked.connect(self.display_subjects_graph)
        self.attendance_button.clicked.connect(self.display_attendance_graph)
        self.aggregated_button.clicked.connect(self.display_aggregated_graph)
        back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.name_list)
        layout.addWidget(self.subject_button)
        layout.addWidget(self.attendance_button)
        layout.addWidget(self.aggregated_button)
        layout.addWidget(back_button)
        self.setLayout(layout)

    def disable_buttons(self) -> None:
        """Disables per-subject or aggregated graph buttons."""
        self.subject_button.setEnabled(False)
        self.attendance_button.setEnabled(False)
        self.aggregated_button.setEnabled(False)

    def resolve_pupil_name(self) -> str:
        assert self.selected_index is not None
        return self.summaries[-1].pupils[self.selected_index].name

    def display_subjects_graph(self) -> None:
        if self.selected_index is None:
            return
        try:
            graph = PupilSubjectPeriodicAveragesGraph(self.app, self.summaries, self.resolve_pupil_name())
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.app.show_error_box(str(e))

    def display_attendance_graph(self) -> None:
        if self.selected_index is None:
            return
        try:
            graph = PupilPeriodicAttendanceGraph(self.app, self.summaries, self.resolve_pupil_name())
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.app.show_error_box(str(e))

    def display_aggregated_graph(self) -> None:
        if self.selected_index is None:
            return
        try:
            graph = PupilPeriodicAveragesGraph(self.app, self.summaries, self.resolve_pupil_name())
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.app.show_error_box(str(e))

    def update_data(self, summaries: List[ClassPeriodReportSummary]) -> None:
        """Updates widget data."""
        self.summaries = summaries
        self.name_list.clearSelection()
        self.name_list.clear()
        for i, name in enumerate([p.name for p in summaries[-1].pupils]):
            self.name_list.insertItem(i, name)
        self.disable_buttons()


class LoginWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel((
            "Prisijungkite prie 'Mano Dienynas' sistemos.\n"
            "Naudokite tokius pat duomenis, kuriuos naudotumėte prisijungdami per naršyklę."
        ))
        self.username_field = QtWidgets.QLineEdit()
        self.username_field.setPlaceholderText("Jūsų el. paštas")
        self.password_field = QtWidgets.QLineEdit()
        self.password_field.setPlaceholderText("Slaptažodis")
        self.password_field.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login_button = QtWidgets.QPushButton('Prisijungti')
        self.back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        self.login_button.clicked.connect(self.login)
        self.back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.username_field)
        layout.addWidget(self.password_field)
        layout.addWidget(self.login_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent) -> None:
        """Intercepts enter key event and calls login function."""
        if key_event.key() == Qt.Key_Return:
            if self.login_button.isEnabled():
                self.login()
        else:
            super().keyPressEvent(key_event)

    def fill_fields(self) -> None:
        """Fills the input fields with default and saved values."""
        self.username_field.setText(self.app.settings.username or "")

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

    def on_success_signal(self, role_selected: bool) -> None:
        """Callback of LoginTaskWorker thread on success."""
        self.login_thread.quit()
        self.enable_gui()
        if role_selected:
            self.app.select_class_widget.update_data()
            return self.app.change_stack(self.app.SELECT_CLASS_WIDGET)
        self.app.select_user_role_widget.update_list()
        self.app.change_stack(self.app.SELECT_USER_ROLE_WIDGET)

    def login(self) -> None:
        """Attempt to log into Mano Dienynas.

        Starts a LoginTask worker thread."""
        username = self.username_field.text()
        password = self.password_field.text()

        if username.strip() == "" or password.strip() == "":
            return self.propagate_error("Įveskite prisijungimo duomenis!")

        self.disable_gui()
        self.login_worker = LoginTaskWorker(self.app, username, password)
        self.login_thread = QtCore.QThread()
        self.login_worker.moveToThread(self.login_thread)

        # Connect signals
        self.login_worker.error.connect(self.on_error_signal) # type: ignore
        self.login_worker.success.connect(self.on_success_signal) # type: ignore
        self.login_thread.started.connect(self.login_worker.login)

        self.login_thread.start()


class SelectUserRoleWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite vartotojo tipą. Jis bus naudojamas nagrinėjamai klasei pasirinkti.")
        self.role_list = QtWidgets.QListWidget()
        self.select_button = QtWidgets.QPushButton('Pasirinkti')
        self.back_button = QtWidgets.QPushButton('Atsijungti ir grįžti į pradžią')

        self.role_list.itemSelectionChanged.connect(self.select_role)
        self.select_button.clicked.connect(self.change_role)
        self.back_button.clicked.connect(self.log_out_and_return)

        layout.addWidget(label)
        layout.addWidget(self.role_list)
        layout.addWidget(self.select_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def log_out_and_return(self) -> None:
        self.app.client.logout()
        self.app.go_to_back()

    def enable_gui(self) -> None:
        """Enables GUI components."""
        self.select_button.setEnabled(True)
        self.back_button.setEnabled(True)

    def disable_gui(self) -> None:
        """Disables GUI components."""
        self.select_button.setEnabled(False)
        self.select_button.clearFocus()
        self.back_button.setEnabled(False)

    def propagate_error(self, error_msg: str) -> None:
        """Display an error and re-enable the GUI."""
        self.enable_gui()
        self.app.show_error_box(error_msg)

    def on_error_signal(self, error: str) -> None:
        """Callback of ChangeRoleWorker thread on error."""
        self.propagate_error(error)
        self.worker_thread.quit()

    def on_success_signal(self) -> None:
        """Callback of ChangeRoleWorker thread on success."""
        self.worker_thread.quit()
        self.enable_gui()
        self.app.select_class_widget.update_data()
        self.app.change_stack(self.app.SELECT_CLASS_WIDGET)

    def select_role(self) -> None:
        # Not best practise, but bash me all you want
        indexes = self.role_list.selectedIndexes()
        if len(indexes) == 0:
            return
        index = indexes[0].row() # type: ignore
        self.select_button.setEnabled(True)
        self.selected_index = index

    def update_list(self):
        self.select_button.setEnabled(False)
        self.role_list.clearSelection()
        self.role_list.clear()
        for i, role in enumerate(self.app.client.get_filtered_user_roles()):
            self.role_list.insertItem(i, role.representable_name)

    def change_role(self) -> None:
        """Creates a change role worker."""
        self.disable_gui()
        assert self.selected_index is not None
        self.worker = ChangeRoleWorker(self.app, self.selected_index)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker.error.connect(self.on_error_signal) # type: ignore
        self.worker.success.connect(self.on_success_signal) # type: ignore
        self.worker_thread.started.connect(self.worker.change_role)

        self.worker_thread.start()


class SelectClassWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite nagrinėjamą klasę.")
        self.class_list = QtWidgets.QListWidget()
        self.classes: List[Class] = []
        self.semester_button = QtWidgets.QPushButton('Generuoti trimestrų/pusmečių ataskaitas')
        self.monthly_button = QtWidgets.QPushButton('Generuoti mėnesines ataskaitas')
        self.back_button = QtWidgets.QPushButton('Grįžti į pradžią')
        self.progress_dialog = None

        self.class_list.itemSelectionChanged.connect(self.select_class)
        self.semester_button.clicked.connect(self.generate_periodic_reports)
        self.monthly_button.clicked.connect(self.generate_monthly_reports)
        self.back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.class_list)
        layout.addWidget(self.semester_button)
        layout.addWidget(self.monthly_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def _create_progress_dialog(self):
        self.progress_dialog = QtWidgets.QProgressDialog("Generuojamos ataskaitos", None, 0, 0, self)
        self.progress_dialog.setWindowFlags(Qt.Window | Qt.MSWindowsFixedSizeDialogHint | Qt.CustomizeWindowHint)
        self.progress_dialog.setModal(True)

    def select_class(self) -> None:
        indexes = self.class_list.selectedIndexes()
        if len(indexes) == 0:
            return
        index = indexes[0].row() # type: ignore
        self.semester_button.setEnabled(True)
        self.monthly_button.setEnabled(True)
        self.selected_index = index

    def enable_gui(self) -> None:
        """Enables GUI components."""
        self.class_list.setEnabled(True)
        self.semester_button.setEnabled(True)
        self.monthly_button.setEnabled(True)
        self.back_button.setEnabled(True)

    def disable_gui(self) -> None:
        """Disables GUI components."""
        self.class_list.setEnabled(False)
        self.semester_button.setEnabled(False)
        self.semester_button.clearFocus()
        self.monthly_button.setEnabled(False)
        self.monthly_button.clearFocus()
        self.back_button.setEnabled(False)

    def propagate_error(self, error_msg: str) -> None:
        """Display an error and re-enable the GUI."""
        self.enable_gui()
        self.app.show_error_box(error_msg)

    def on_error_signal(self, error: str) -> None:
        """Callback of GenerateReportWorker thread on error."""
        self.propagate_error(error)
        if self.progress_dialog:
            self.progress_dialog.hide()
        self.worker_thread.quit()

    def on_progress_signal(self, data: Tuple[int, int]) -> None:
        """Callback of GenerateReportWorker thread on success."""
        total, curr = data

        if self.progress_dialog is None:
            self._create_progress_dialog()

        assert self.progress_dialog is not None

        if not self.progress_dialog.isVisible():
            self.progress_dialog.show()
        self.progress_dialog.setRange(0, total)
        self.progress_dialog.setValue(curr)

    def on_success_signal(self, file_paths: List[str]) -> None:
        """Callback of GenerateReportWorker thread on success."""
        if self.progress_dialog:
            self.progress_dialog.hide()
        self.worker_thread.quit()
        sums = self.app.generate_periodic_summaries(file_paths)
        sums.sort(key=lambda s: (s.term_start))
        if self.app.view_attendance:
            self.app.display_attendance_monthly_graph(sums)
            return self.enable_gui()
        if self.app.view_aggregated:
            self.app.display_aggregated_monthly_graph(sums)
            return self.enable_gui()
        self.app.display_pupil_monthly_graph_selector(sums)
        self.enable_gui()

    def update_data(self) -> None:
        self.enable_gui()
        self.classes = self.app.client.get_class_averages_report_options() # type: ignore
        if isinstance(self.classes, UnifiedAveragesReportGenerator):
            return
        self.semester_button.setEnabled(False)
        self.monthly_button.setEnabled(False)
        self.class_list.clearSelection()
        self.class_list.clear()
        for i, class_o in enumerate(self.classes):
            self.class_list.insertItem(i, class_o.name)

    def generate_periodic_reports(self) -> None:
        """Starts GenerateReportWorker thread for periodic reports."""
        self.disable_gui()
        assert self.selected_index is not None
        self.worker = GenerateReportWorker(self.app, self.classes[self.selected_index])
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.error.connect(self.on_error_signal) # type: ignore
        self.worker.success.connect(self.on_success_signal) # type: ignore
        self.worker.progress.connect(self.on_progress_signal) # type: ignore
        self.worker_thread.started.connect(self.worker.generate_periodic)
        self.worker_thread.start()

    def generate_monthly_reports(self) -> None:
        """Starts GenerateReportWorker thread for monthly reports."""
        self.disable_gui()
        assert self.selected_index is not None
        self.worker = GenerateReportWorker(self.app, self.classes[self.selected_index])
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.error.connect(self.on_error_signal) # type: ignore
        self.worker.success.connect(self.on_success_signal) # type: ignore
        self.worker.progress.connect(self.on_progress_signal) # type: ignore
        self.worker_thread.started.connect(self.worker.generate_monthly)
        self.worker_thread.start()


class SettingsWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.unsaved = False

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Programos nustatymai")
        self.save_button = QtWidgets.QPushButton('Išsaugoti pakeitimus')
        self.back_button = QtWidgets.QPushButton('Grįžti į pradžią')

        self.save_button.clicked.connect(self.on_save_button_click)
        self.back_button.clicked.connect(self.on_return_button_click)

        settings_layout = QtWidgets.QFormLayout()
        self.last_dir_label = QtWidgets.QLabel()
        self.debugging_checkbox = QtWidgets.QCheckBox()
        self.hide_names_checkbox = QtWidgets.QCheckBox()
        self.flip_names_checkbox = QtWidgets.QCheckBox()
        self.outline_values_checkbox = QtWidgets.QCheckBox()
        self.save_path_button = QtWidgets.QPushButton("Atidaryti")

        self.debugging_checkbox.clicked.connect(self.on_debugging_checkbox_click)
        self.hide_names_checkbox.clicked.connect(self.on_hide_names_checkbox_click)
        self.flip_names_checkbox.clicked.connect(self.on_flip_names_checkbox_click)
        self.outline_values_checkbox.clicked.connect(self.on_outline_values_checkbox_click)
        self.save_path_button.clicked.connect(self.on_save_path_button_click)

        settings_layout.addRow(QtWidgets.QLabel("Paskutinė rankiniu būdu analizuota vieta:"), self.last_dir_label)
        settings_layout.addRow(QtWidgets.QLabel("Kūrėjo režimas:"), self.debugging_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Demonstracinis režimas:"), self.hide_names_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Apversti vardus (grafikuose):"), self.flip_names_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Rodyti kontūrus (grafikų vertėse):"), self.outline_values_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Programos duomenys:"), self.save_path_button)

        layout.addWidget(label, alignment=Qt.AlignTop) # type: ignore
        layout.addLayout(settings_layout)
        layout.addWidget(self.save_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def on_save_button_click(self) -> None:
        self.save_state()

    def on_return_button_click(self) -> None:
        self.app.go_to_back()

    def on_debugging_checkbox_click(self) -> None:
        self.unsaved = True
        self.app.settings.debugging = self.debugging_checkbox.isChecked()

    def on_hide_names_checkbox_click(self) -> None:
        self.unsaved = True
        self.app.settings.hide_names = self.hide_names_checkbox.isChecked()

    def on_flip_names_checkbox_click(self) -> None:
        self.unsaved = True
        self.app.settings.flip_names = self.flip_names_checkbox.isChecked()

    def on_outline_values_checkbox_click(self) -> None:
        self.unsaved = True
        self.app.settings.outlined_values = self.outline_values_checkbox.isChecked()

    def on_save_path_button_click(self) -> None:
        open_path(get_data_dir())

    def load_state(self) -> None:
        self.last_dir_label.setText(self.app.settings.last_dir or "nėra")
        self.debugging_checkbox.setChecked(self.app.settings.debugging)
        self.hide_names_checkbox.setChecked(self.app.settings.hide_names)
        self.flip_names_checkbox.setChecked(self.app.settings.flip_names)
        self.outline_values_checkbox.setChecked(self.app.settings.outlined_values)

    def save_state(self) -> None:
        self.unsaved = False
        self.app.settings.last_ver = list(__VERSION__)
        self.app.settings.save()
        self.app.change_stack(App.MAIN_WIDGET)

class App(QtWidgets.QWidget):

    MAIN_WIDGET = 0
    SELECT_GRAPH_DATA_WIDGET = 1
    SELECT_PUPIL_WIDGET = 2
    LOGIN_WIDGET = 3
    SELECT_USER_ROLE_WIDGET = 4
    SELECT_CLASS_WIDGET = 5
    SETTINGS_WIDGET = 6

    def __init__(self, settings: Settings):
        super().__init__()
        logger.info("App instance initialised")
        logger.info(f'Running on {platform.system()} v{platform.version()} [{platform.machine()}]')

        self.settings = settings
        self.debug = settings.debugging
        self.client = Client()

        if self.debug:
            logger.setLevel(logging.DEBUG)
            fh.setLevel(logging.DEBUG)
            if ch:
                ch.setLevel(logging.DEBUG)
            logger.debug(f"Loaded modules: {list(sys.modules.keys())}")

        self.view_aggregated = False
        self.view_attendance = False

        self.setWindowTitle('Mokinių pasiekimų ir lankomumo stebėsenos sistema')
        self.setWindowIcon(QtGui.QIcon(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        ))

        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480

        self.stack = QtWidgets.QStackedWidget()

        # Initialize QWidgets
        self.main_widget = MainWidget(self)
        self.select_graph_widget = SelectGraphWidget(self)
        self.select_pupil_widget = PupilSelectionWidget(self)
        self.login_widget = LoginWidget(self)
        self.select_user_role_widget = SelectUserRoleWidget(self)
        self.select_class_widget = SelectClassWidget(self)
        self.settings_widget = SettingsWidget(self)
        self.matplotlib_window = MatplotlibWindow(self)

        # Add said widgets to the StackedWidget
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(self.select_graph_widget)
        self.stack.addWidget(self.select_pupil_widget)
        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.select_user_role_widget)
        self.stack.addWidget(self.select_class_widget)
        self.stack.addWidget(self.settings_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def go_to_back(self) -> None:
        """Return to the main widget."""
        self.view_aggregated = False
        self.view_attendance = False
        self.change_stack(self.MAIN_WIDGET)

    def change_stack(self, index: int) -> None:
        """Change current stack widget."""
        self.stack.setCurrentIndex(index)

    def view_settings(self) -> None:
        """Opens the settings widget."""
        self.settings_widget.load_state()
        self.change_stack(self.SETTINGS_WIDGET)

    def view_aggregated_monthly_selector(self):
        self.view_aggregated = True
        self.change_stack(self.SELECT_GRAPH_DATA_WIDGET)

    def view_attendance_monthly_selector(self):
        self.view_attendance = True
        self.change_stack(self.SELECT_GRAPH_DATA_WIDGET)

    def view_pupil_monthly_selector(self):
        self.view_aggregated = False
        self.change_stack(self.SELECT_GRAPH_DATA_WIDGET)

    def determine_graph_type(self):
        filenames = self.ask_files_dialog()
        if len(filenames) == 0:
            return

        summaries = self.generate_periodic_summaries(filenames)
        if len(summaries) == 0:
            return self.show_error_box("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")

        # Sort summaries by term start, ascending (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))
        if self.view_attendance:
            return self.display_attendance_monthly_graph(summaries)
        if self.view_aggregated:
            return self.display_aggregated_monthly_graph(summaries)
        self.display_pupil_monthly_graph_selector(summaries)

    def initUI(self):
        self.setGeometry(self.left, self.top, self.w, self.h)
        center = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen()).center()
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
            logger.error("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
        logger.debug(f"Pusmečių/trimestrų suvestinės sugeneruotos: {len(summaries)}")
        return summaries

    def generate_periodic_summaries(self, files: List[str]) -> List[ClassPeriodReportSummary]:
        """Generates a list of periodic summaries."""
        summaries: List[ClassPeriodReportSummary] = []
        for filename in files:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilPeriodicReportParser(filename)
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

            if any(s.average is None for s in summary.students):
                logger.warn(f"{base_name}: bent vieno mokinio vidurkis yra ne-egzistuojantis, neskaitoma")
                continue

            logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
            summaries.append(summary)

        if len(summaries) == 0:
            logger.error("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
        logger.debug(f"Laikotarpių suvestinės sugeneruotos: {len(summaries)}")
        return summaries

    def view_aggregated_semester_graph(self) -> None:
        files = self.ask_files_dialog()
        if len(files) == 0:
            return

        if self.debug:
            for file in files:
                logger.debug(f"File selected: {file}")

        summaries = self.generate_semester_summaries(files)
        if len(summaries) == 0:
            return self.show_error_box("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")

        # Sort summaries by
        # 1) term start (year)
        # 2) type (semester) (I -> II -> III)
        summaries.sort(key=lambda s: (s.term_start, s.type_as_int))
        self.display_aggregated_semester_graph(summaries)

    def display_aggregated_semester_graph(self, summaries: List[ClassSemesterReportSummary]) -> None:
        try:
            graph = UnifiedClassAveragesGraph(self, summaries)
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.show_error_box(str(e))

    def display_aggregated_monthly_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        try:
            graph = UnifiedClassAveragesGraph(self, summaries)
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.show_error_box(str(e))
        self.go_to_back()

    def display_attendance_monthly_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        try:
            graph = UnifiedClassAttendanceGraph(self, summaries)
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.show_error_box(str(e))
        self.go_to_back()

    def display_pupil_monthly_graph_selector(self, summaries: List[ClassPeriodReportSummary]):
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.update_data(summaries)
        self.change_stack(self.SELECT_PUPIL_WIDGET)

    def show_error_box(self, message: str) -> None:
        """Displays a native error dialog."""
        QtWidgets.QMessageBox.critical(
            self, "Įvyko klaida", message,
            QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton
        )

    def ask_files_dialog(self, caption: str = "Pasirinkite Excel ataskaitų failus") -> List[str]:
        """Displays a file selection dialog for picking Excel files."""
        directory = self.settings.last_dir
        if directory is None or not os.path.exists(directory):
            directory = os.path.join(get_home_dir(), "Downloads")

        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
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
