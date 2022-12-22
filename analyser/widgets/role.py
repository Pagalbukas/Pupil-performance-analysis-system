from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Optional

from analyser.qt_compat import QtWidgets, QtCore

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

class ChangeRoleWorker(QtCore.QObject):
    success = QtCore.Signal(int)
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
        self.success.emit(self.index)

class SelectUserRoleWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.selected_index: Optional[int] = None

        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Pasirinkite vartotojo tipą. Jis bus naudojamas nagrinėjamai klasei ar grupei pasirinkti.")
        self.role_list = QtWidgets.QListWidget()
        self.select_button = QtWidgets.QPushButton("Pasirinkti")
        self.back_button = QtWidgets.QPushButton("Atsijungti ir grįžti į pradžią")

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
        self.worker_thread.quit()
        self.propagate_error(error)

    def on_success_signal(self, role_idx: int) -> None:
        """Callback of ChangeRoleWorker thread on success."""
        self.worker_thread.quit()
        self.enable_gui()
        
        role = self.app.client.get_filtered_user_roles()[role_idx]
        if role.is_teacher:
            self.app.open_group_selector()
        else:
            self.app.open_class_selector()

    def select_role(self) -> None:
        # Not best practise, but bash me all you want
        indexes = self.role_list.selectedIndexes()
        if len(indexes) == 0:
            return
        index = indexes[0].row() # type: ignore
        self.select_button.setEnabled(True)
        self.selected_index = index

    def update_role_list(self):
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
