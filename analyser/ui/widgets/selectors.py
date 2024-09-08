from __future__ import annotations

import logging

from typing import TYPE_CHECKING, List, Optional, Tuple

from analyser.mano_dienynas.client import Group, Class # type: ignore
from analyser.mano_dienynas.parsing import parse_group_summary_file, parse_periodic_summary_files
from analyser.ui.qt_compat import QtWidgets, QtCore, Qt

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.ui.app import App

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

class FetchClassesWorker(QtCore.QObject):
    success = QtCore.Signal(list)
    error = QtCore.Signal(str)

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

    @QtCore.Slot() # type: ignore
    def fetch_classes(self) -> None:
        try:
            classes = self.app.client.get_class_averages_report_options() # type: ignore
            assert isinstance(classes, list)
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e)) # type: ignore
        self.success.emit(classes) # type: ignore

class FetchGroupsWorker(QtCore.QObject):
    success = QtCore.Signal(list)
    error = QtCore.Signal(str)

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

    @QtCore.Slot() # type: ignore
    def fetch_groups(self) -> None:
        try:
            groups = self.app.client.fetch_user_groups() # type: ignore
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e)) # type: ignore
        self.success.emit(groups) # type: ignore

class GenerateGroupReportWorker(QtCore.QObject):
    success = QtCore.Signal(list)
    error = QtCore.Signal(str)
    progress = QtCore.Signal(tuple)

    def __init__(self, app: App, group: Group) -> None:
        super().__init__()
        self.app = app
        self.group = group

    @QtCore.Slot() # type: ignore
    def generate_report(self):
        try:
            generator = self.app.client.fetch_group_report_options(self.group.id)
            self.progress.emit((1, 0))
            files = []
            for i, file in enumerate(generator.generate_report()):
                self.progress.emit((1, i + 1))
                files.append(file)
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))
        self.success.emit(files)

class GenericGeneratorWidget(QtWidgets.QWidget):
    pass

class GroupGeneratorWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite nagrinėjamą grupę.")
        self.group_list = QtWidgets.QListWidget()
        self.groups: List[Group] = []
        self.generate_button = QtWidgets.QPushButton("Generuoti ataskaitą")
        self.back_button = QtWidgets.QPushButton('Grįžti į pradžią')
        self.progress_dialog = None

        self.group_list.itemSelectionChanged.connect(self.select_group)
        self.generate_button.clicked.connect(self.generate_report)
        self.back_button.clicked.connect(self.app.go_to_back)

        layout.addWidget(label)
        layout.addWidget(self.group_list)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def _create_progress_dialog(self):
        self.progress_dialog = QtWidgets.QProgressDialog("Generuojama ataskaita", None, 0, 0, self)
        self.progress_dialog.setWindowFlags(Qt.Window | Qt.MSWindowsFixedSizeDialogHint | Qt.CustomizeWindowHint)
        self.progress_dialog.setModal(True)

    def fetch_group_data(self) -> None:
        self.disable_gui()
        self.worker = FetchGroupsWorker(self.app)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.success.connect(self._on_fetch_success) # type: ignore
        self.worker.error.connect(self._on_fetch_failure) # type: ignore
        self.worker_thread.started.connect(self.worker.fetch_groups)
        self.worker_thread.start()
    
    def _on_fetch_success(self, groups: List[Group]) -> None:
        self.worker_thread.quit()
        self.groups = groups
        self.group_list.clearSelection()
        self.group_list.clear()
        for i, group in enumerate(self.groups):
            self.group_list.insertItem(i, group.name)
        self.enable_gui()
    
    def _on_fetch_failure(self, error: str) -> None:
        self.worker_thread.quit()
        self.propagate_error(error)

    def select_group(self) -> None:
        indexes = self.group_list.selectedIndexes()
        if len(indexes) == 0:
            return
        index = indexes[0].row() # type: ignore
        self.generate_button.setEnabled(True)
        self.selected_index = index

    def enable_gui(self) -> None:
        """Enables GUI components."""
        self.group_list.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.back_button.setEnabled(True)

    def disable_gui(self) -> None:
        """Disables GUI components."""
        self.group_list.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.generate_button.clearFocus()
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
        
        summary = parse_group_summary_file(file_paths[0])
        self.app.open_group_type_selector(summary)
        self.enable_gui()

    def generate_report(self) -> None:
        """Starts GenerateReportWorker thread for monthly reports."""
        self.disable_gui()
        assert self.selected_index is not None
        self.worker = GenerateGroupReportWorker(self.app, self.groups[self.selected_index])
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.error.connect(self.on_error_signal) # type: ignore
        self.worker.success.connect(self.on_success_signal) # type: ignore
        self.worker.progress.connect(self.on_progress_signal) # type: ignore
        self.worker_thread.started.connect(self.worker.generate_report)
        self.worker_thread.start()


class ClassGeneratorWidget(QtWidgets.QWidget):

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

    def fetch_class_data(self) -> None:
        self.disable_gui()
        self.worker = FetchClassesWorker(self.app)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.success.connect(self._on_fetch_success) # type: ignore
        self.worker.error.connect(self._on_fetch_failure) # type: ignore
        self.worker_thread.started.connect(self.worker.fetch_classes)
        self.worker_thread.start()
    
    def _on_fetch_success(self, classes: List[Class]) -> None:
        self.worker_thread.quit()
        self.classes = classes
        self.class_list.clearSelection()
        self.class_list.clear()
        for i, class_o in enumerate(self.classes):
            self.class_list.insertItem(i, class_o.name)
        self.enable_gui()
    
    def _on_fetch_failure(self, error: str) -> None:
        self.worker_thread.quit()
        self.propagate_error(error)

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
