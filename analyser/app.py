from __future__ import annotations

import os
import platform
import sys
import logging
import traceback

from logging.handlers import RotatingFileHandler
from typing import List, Optional

from analyser.files import EXECUTABLE_PATH, get_home_dir, get_log_file
from analyser.graphing import (
    AnyGraph, ClassAttendanceGraph, ClassAveragesGraph, GroupAveragesGraph
)
from analyser.mano_dienynas.client import Client # type: ignore
from analyser.settings import Settings
from analyser.summaries import ClassPeriodReportSummary, GroupReportSummary
from analyser.qt_compat import QtWidgets, QtGui
from analyser.widgets.graph import MatplotlibWindow
from analyser.widgets.main import MainWidget
from analyser.widgets.login import LoginWidget
from analyser.widgets.role import SelectUserRoleWidget
from analyser.widgets.selectors import ClassGeneratorWidget, GroupGeneratorWidget
from analyser.widgets.settings import SettingsWidget
from analyser.widgets.type_selector import ManualFileSelectorWidget
from analyser.widgets.view import GroupPupilSelectionWidget, GroupViewTypeSelectorWidget, PeriodicViewTypeSelectorWidget, ClassPupilSelectionWidget

__VERSION__ = (1, 4, 0, 0)
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
    SETTINGS_WIDGET = 1
    FILE_SELECTOR_WIDGET = 2
    LOGIN_WIDGET = 3
    ROLE_SELECTOR_WIDGET = 4
    PERIODIC_TYPE_SELECTOR = 5
    GROUP_TYPE_SELECTOR = 6
    CLASS_GENERATOR = 7
    GROUP_GENERATOR = 8
    CLASS_PUPIL_SELECTOR = 9
    GROUP_PUPIL_SELECTOR = 10

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
        self.role_selector_widget = SelectUserRoleWidget(self)
        
        # Initialise selectors and generators
        self.periodic_view_selector_widget = PeriodicViewTypeSelectorWidget(self)
        self.group_view_selector_widget = GroupViewTypeSelectorWidget(self)
        self.class_generator_widget = ClassGeneratorWidget(self)
        self.group_generator_widget = GroupGeneratorWidget(self)
        self.class_pupil_selector_widget = ClassPupilSelectionWidget(self)
        self.group_pupil_selector_widget = GroupPupilSelectionWidget(self)

        # Add said widgets to the StackedWidget
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(self.settings_widget)
        self.stack.addWidget(self.file_selector_widget)
        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.role_selector_widget)
        self.stack.addWidget(self.periodic_view_selector_widget)
        self.stack.addWidget(self.group_view_selector_widget)
        self.stack.addWidget(self.class_generator_widget)
        self.stack.addWidget(self.group_generator_widget)
        self.stack.addWidget(self.class_pupil_selector_widget)
        self.stack.addWidget(self.group_pupil_selector_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.initUI()

    def set_window_title(self, section: str):
        if section is None:
            return self.setWindowTitle(f'Mokinių pasiekimų ir lankomumo stebėsenos sistema')
        self.setWindowTitle(f'Mokinių pasiekimų ir lankomumo stebėsenos sistema | {section}')

    def _display_graph(self, graph: AnyGraph):
        try:
            graph.display()
        except Exception as e:
            logger.exception(e)
            return self.show_error_box(str(e))
        
    def display_semester_pupil_averages_graph(self, summaries):
        self._display_graph(ClassAveragesGraph(self, summaries))

    def display_period_pupil_averages_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        self._display_graph(ClassAveragesGraph(self, summaries))

    def display_period_attendance_graph(self, summaries: List[ClassPeriodReportSummary]) -> None:
        self._display_graph(ClassAttendanceGraph(self, summaries))

    def display_group_pupil_marks_graph(self, summary: GroupReportSummary) -> None:
        self._display_graph(GroupAveragesGraph(self, summary))

    def go_to_back(self) -> None:
        """Return to the main widget."""
        self.set_window_title("Pagrindinis")
        self.change_stack(self.MAIN_WIDGET)
        
    def open_periodic_type_selector(self, summaries):
        self.periodic_view_selector_widget._update_summary_list(summaries)
        self.set_window_title("Klasės grafiko tipas")
        self.change_stack(self.PERIODIC_TYPE_SELECTOR)

    def open_group_type_selector(self, summary: GroupReportSummary):
        self.group_view_selector_widget._update_summary_list(summary)
        self.set_window_title("Grupės grafiko tipas")
        self.change_stack(self.GROUP_TYPE_SELECTOR)
        
    def open_individual_period_pupil_graph_selector(self, summaries):
        self.class_pupil_selector_widget.disable_buttons()
        self.class_pupil_selector_widget.update_data(summaries)
        self.set_window_title("Nagrinėjamas mokinys")
        self.change_stack(self.CLASS_PUPIL_SELECTOR)
    
    def open_individual_group_pupil_graph_selector(self, summary: GroupReportSummary):
        self.group_pupil_selector_widget.disable_buttons()
        self.group_pupil_selector_widget.update_data(summary)
        self.set_window_title("Nagrinėjamas mokinys")
        self.change_stack(self.GROUP_PUPIL_SELECTOR)

    def open_class_selector(self):
        self.class_generator_widget.fetch_class_data()
        self.set_window_title("Nagrinėjama klasė")
        self.change_stack(self.CLASS_GENERATOR)
    
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

    def _show_error_box(self, title: str, message: str) -> None:
        """Displays a native error dialog."""
        QtWidgets.QMessageBox.critical(
            self, title, message,
            QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton
        )

    def show_error_box(self, message: str) -> None:
        """Displays a native error dialog."""
        self._show_error_box("Įvyko klaida", message)

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
    
    def ask_file_dialog(self, caption: str = "Pasirinkite Excel ataskaitos failą") -> Optional[str]:
        """Displays a file selection dialog for picking an Excel file."""
        directory = self.settings.last_dir
        if directory is None or not os.path.exists(directory):
            directory = os.path.join(get_home_dir(), "Downloads")

        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption,
            directory,
            "Excel ataskaitos failas (*.xlsx *.xls)"
        )

        # Store the last dir in the settings
        if file_name == '':
            return None

        self.settings.last_dir = os.path.dirname(file_name)
        self.settings.save()
        return file_name
    
    def excepthook(self, exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).strip()
        logger.critical(tb)
        self._show_error_box(
            "Įvyko nenumatyta klaida",
            f'{tb}\n\nPrograma savo darbo tęsti nebegali ir užsidarys.'
        )
        QtWidgets.QApplication.exit(1)
