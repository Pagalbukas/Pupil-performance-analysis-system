from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from analyser.qt_compat import QtWidgets, QtCore, QtGui, Qt

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

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
                "Kol kas palaikomos tik paskyros su 'Klasės vadovas' ir 'Sistemos administratorius' tipais.\n"
                "Jeigu esate dalyko mokytojas, programa kol kas negali automatiškai atsiųsti grupių ataskaitų. "
                "Tai reikia padaryti rankiniu būdų, atsisiunčiant 'Ataskaita pagal grupę' visiems metams."
            )

        # Attempt automatic role change
        if len(roles) == 1:
            if not roles[0].is_active:
                try:
                    roles[0].change_role()
                except Exception as e:
                    logger.exception(e)
                    return self.error.emit(str(e))
            logger.info(f"Paskyros tipas pasirinktas automatiškai į '{roles[0].title}'")

        self.success.emit(len(roles) == 1)

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
            self.app.set_window_title("Nagrinėjama klasė")
            return self.app.change_stack(self.app.SELECT_CLASS_WIDGET)
        self.app.select_user_role_widget.update_list()
        self.app.set_window_title("Vartotojo tipas")
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