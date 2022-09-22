from __future__ import annotations

import os
import platform
import sys
import logging

from logging.handlers import RotatingFileHandler
from typing import List

from analyser.files import EXECUTABLE_PATH, get_home_dir, get_log_file
from analyser.graphing import (
    MatplotlibWindow, UnifiedClassAveragesGraph, UnifiedClassAttendanceGraph, UnifiedGroupAveragesGraph
)
from analyser.mano_dienynas.client import Client # type: ignore
from analyser.settings import Settings
from analyser.summaries import ClassPeriodReportSummary
from analyser.qt_compat import QtWidgets, QtGui
from analyser.widgets.main import MainWidget
from analyser.widgets.login import LoginWidget
from analyser.widgets.role import SelectUserRoleWidget
from analyser.widgets.selectors import ClassGeneratorWidget, GroupGeneratorWidget
from analyser.widgets.settings import SettingsWidget
from analyser.widgets.type_selector import ManualFileSelectorWidget
from analyser.widgets.view import GroupViewTypeSelectorWidget, PeriodicViewTypeSelectorWidget, PupilSelectionWidget

__VERSION__ = (1, 3, 0, 2)
__VERSION_NAME__ = f"{__VERSION__[0]}.{__VERSION__[1]}.{__VERSION__[2]}.{__VERSION__[3]}"
REPO_URL = "https://mokytojams.svetikas.lt/"

logger = logging.getLogger("analizatorius")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(f'[%(asctime)s %(name)s-{__VERSION_NAME__}:%(levelname)s]: %(message)s', "%Y-%m-%d %H:%M:%S")

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
    GROUP_GENERATOR = 10

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

        self.set_window_title("Pagrindinis")
        self.setWindowIcon(QtGui.QIcon(
            os.path.join(EXECUTABLE_PATH, 'icon.png')
        ))

        self.left = 10
        self.top = 10
        self.w = 640
        self.h = 480

        self.stack = QtWidgets.QStackedWidget()
        
        # Initialize core widgets
        self.main_widget = MainWidget(self)
        self.settings_widget = SettingsWidget(self)
        self.matplotlib_window = MatplotlibWindow(self)
        
        # Initialize file selection/generation widgets
        self.file_selector_widget = ManualFileSelectorWidget(self)
        self.login_widget = LoginWidget(self)
        
        # Initialise selectors
        self.periodic_view_selector_widget = PeriodicViewTypeSelectorWidget(self)
        self.group_view_selector_widget = GroupViewTypeSelectorWidget(self)
        
        self.class_generator_widget = ClassGeneratorWidget(self)
        self.group_generator_widget = GroupGeneratorWidget(self)

        # Initialize QWidgets
        dummy = Dummy()
        self.select_pupil_widget = PupilSelectionWidget(self)
        self.select_user_role_widget = SelectUserRoleWidget(self)
        self.select_class_widget = ClassGeneratorWidget(self)

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
        self.stack.addWidget(self.group_generator_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def set_window_title(self, section: str):
        if section is None:
            return self.setWindowTitle(f'Mokinių pasiekimų ir lankomumo stebėsenos sistema')
        self.setWindowTitle(f'Mokinių pasiekimų ir lankomumo stebėsenos sistema | {section}')

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

    def display_group_pupil_marks_graph(self, summary: ClassPeriodReportSummary) -> None:
        self._display_graph(UnifiedGroupAveragesGraph(self, summary))

    def go_to_back(self) -> None:
        """Return to the main widget."""
        self.set_window_title("Pagrindinis")
        self.change_stack(self.MAIN_WIDGET)
        
    def open_periodic_type_selector(self, summaries):
        self.periodic_view_selector_widget._update_summary_list(summaries)
        self.set_window_title("Klasės grafiko tipas")
        self.change_stack(self.PERIODIC_TYPE_SELECTOR)

    def open_group_type_selector(self, summaries):
        self.group_view_selector_widget._update_summary_list(summaries)
        self.set_window_title("Grupės grafiko tipas")
        self.change_stack(self.GROUP_TYPE_SELECTOR)
        
    def open_individual_period_pupil_graph_selector(self, summaries):
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.update_data(summaries)
        self.set_window_title("Nagrinėjamas mokinys")
        self.change_stack(self.SELECT_PUPIL_WIDGET)
    
    def open_individual_group_pupil_graph_selector(self, summaries):
        self.select_pupil_widget.disable_buttons()
        self.select_pupil_widget.update_data(summaries)
        self.set_window_title("Nagrinėjamas mokinys")
        self.change_stack(self.SELECT_PUPIL_WIDGET)

    def open_class_selector(self):
        self.select_class_widget.fetch_class_data()
        self.set_window_title("Nagrinėjama klasė")
        self.change_stack(self.SELECT_CLASS_WIDGET)
    
    def open_group_selector(self):
        self.group_generator_widget.fetch_group_data()
        self.set_window_title("Nagrinėjama grupė")
        self.change_stack(self.GROUP_GENERATOR)

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
