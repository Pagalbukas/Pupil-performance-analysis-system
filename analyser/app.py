from __future__ import annotations
from ctypes import Union

import os
import platform
import sys
import timeit
import logging

from logging.handlers import RotatingFileHandler
from typing import Any, List, Optional, Tuple

from analyser.errors import ParsingError
from analyser.files import EXECUTABLE_PATH, get_home_dir, get_log_file
from analyser.graphing import (
    MatplotlibWindow, PupilPeriodicAttendanceGraph, PupilPeriodicAveragesGraph, PupilSubjectPeriodicAveragesGraph,
    UnifiedClassAveragesGraph, UnifiedClassAttendanceGraph, UnifiedGroupGraph
)
from analyser.mano_dienynas.client import Client, UnifiedAveragesReportGenerator, Class # type: ignore
from analyser.parsing import GroupPeriodicReportParser, PupilSemesterReportParser, PupilPeriodicReportParser, parse_periodic_summary_files
from analyser.settings import Settings
from analyser.summaries import ClassSemesterReportSummary, ClassPeriodReportSummary
from analyser.qt_compat import QtWidgets, QtCore, QtGui, Qt
from analyser.widgets.main import MainWidget2
from analyser.widgets.login import LoginWidget
from analyser.widgets.settings import SettingsWidget
from analyser.widgets.type_selector import ManualFileSelectorWidget
from analyser.widgets.view import GroupViewTypeSelectorWidget, PeriodicViewTypeSelectorWidget, PupilSelectionWidget

__VERSION__ = (1, 2, 1)
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
        
        summaries = parse_periodic_summary_files(file_paths)
        summaries.sort(key=lambda s: (s.term_start))
        self.app.open_periodic_type_selector(summaries)
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

class Dummy(QtWidgets.QWidget):
    pass

class App(QtWidgets.QWidget):

    MAIN_WIDGET = 0
    DUMMY = 1
    SELECT_PUPIL_WIDGET = 2
    LOGIN_WIDGET = 3
    SELECT_USER_ROLE_WIDGET = 4
    SELECT_CLASS_WIDGET = 5
    SETTINGS_WIDGET = 6

    MANUAL_SELECTOR = 7
    PERIODIC_TYPE_SELECTOR = 8
    GROUP_TYPE_SELECTOR = 9

    def __init__(self, settings: Settings):
        super().__init__()
        self.version = __VERSION__
        logger.info("App instance initialised")
        if platform.system() == "Linux":
            logger.info(f'Running on Linux {platform.release()} [{platform.machine()}]')
        else:
            logger.info(f'Running on {platform.system()} v{platform.version()} [{platform.machine()}]')

        self.settings = settings
        self.debug = settings.debugging
        self.client = Client(settings.mano_dienynas_url)

        if self.debug:
            logger.setLevel(logging.DEBUG)
            fh.setLevel(logging.DEBUG)
            if ch:
                ch.setLevel(logging.DEBUG)
            logger.debug(f"Loaded modules: {list(sys.modules.keys())}")

        self.setWindowTitle('Mokinių pasiekimų ir lankomumo stebėsenos sistema')
        self.setWindowIcon(QtGui.QIcon(
            os.path.join(EXECUTABLE_PATH, 'icon.png')
        ))

        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480

        self.stack = QtWidgets.QStackedWidget()
        
        # Initialize core widgets
        self.main_widget = MainWidget2(self)
        self.settings_widget = SettingsWidget(self)
        self.matplotlib_window = MatplotlibWindow(self)
        
        # Initialize file selection/generation widgets
        self.file_selector_widget = ManualFileSelectorWidget(self)
        
        # Initialise selectors
        self.periodic_view_selector_widget = PeriodicViewTypeSelectorWidget(self)
        self.group_view_selector_widget = GroupViewTypeSelectorWidget(self)

        # Initialize QWidgets
        dummy = Dummy()
        self.select_pupil_widget = PupilSelectionWidget(self)
        self.login_widget = LoginWidget(self)
        self.select_user_role_widget = SelectUserRoleWidget(self)
        self.select_class_widget = SelectClassWidget(self)

        # Add said widgets to the StackedWidget
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(dummy)
        self.stack.addWidget(self.select_pupil_widget)
        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.select_user_role_widget)
        self.stack.addWidget(self.select_class_widget)
        self.stack.addWidget(self.settings_widget)
        
        self.stack.addWidget(self.file_selector_widget)
        self.stack.addWidget(self.periodic_view_selector_widget)
        self.stack.addWidget(self.group_view_selector_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def _display_graph(self, graph: UnifiedClassAveragesGraph):
        try:
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.show_error_box(str(e))
        
    def display_semester_pupil_averages_graph(self, summaries):
        self._display_graph(UnifiedClassAveragesGraph(self, summaries))

    def display_period_pupil_averages_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        self._display_graph(UnifiedClassAveragesGraph(self, summaries))

    def display_period_attendance_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        self._display_graph(UnifiedClassAttendanceGraph(self, summaries))

    def display_group_pupil_marks_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        self._display_graph(UnifiedGroupGraph(self, summaries[0]))

    def go_to_back(self) -> None:
        """Return to the main widget."""
        self.view_aggregated = False
        self.view_attendance = False
        self.change_stack(self.MAIN_WIDGET)
        
    def open_periodic_type_selector(self, summaries):
        self.periodic_view_selector_widget._update_summary_list(summaries)
        self.change_stack(self.PERIODIC_TYPE_SELECTOR)

    def open_group_type_selector(self, summaries):
        self.group_view_selector_widget._update_summary_list(summaries)
        self.change_stack(self.GROUP_TYPE_SELECTOR)
        
    def open_individual_period_pupil_graph_selector(self, summaries):
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.update_data(summaries)
        self.change_stack(self.SELECT_PUPIL_WIDGET)
    
    def open_individual_group_pupil_graph_selector(self, summaries):
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.update_data(summaries)
        self.change_stack(self.SELECT_PUPIL_WIDGET)

    def change_stack(self, index: int) -> None:
        """Change current stack widget."""
        self.stack.setCurrentIndex(index)

    def initUI(self):
        self.setGeometry(self.left, self.top, self.w, self.h)
        center = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen()).center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        self.move(geo.topLeft())
        self.show()

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
