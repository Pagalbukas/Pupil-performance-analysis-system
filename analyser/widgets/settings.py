from __future__ import annotations

import sys
import platform
import webbrowser
import requests # type: ignore
import logging

from typing import TYPE_CHECKING

from analyser.files import get_data_dir, open_path
from analyser.qt_compat import QtWidgets, QtCore, Qt

if TYPE_CHECKING:
    from analyser.app import App

logger = logging.getLogger("analizatorius")

class CheckForUpdatesWorker(QtCore.QObject):
    success = QtCore.Signal(dict)
    error = QtCore.Signal(str)

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

    @QtCore.Slot() # type: ignore
    def search(self):
        try:
            r = requests.get("https://raw.githubusercontent.com/Pagalbukas/Pupil-performance-analysis-system/main/version_data.json")
            data = r.json()
        except Exception as e:
            logger.exception(e)
            return self.error.emit(str(e))
        self.success.emit(data)

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
        self.search_updates_button = QtWidgets.QPushButton("Ieškoti")

        self.debugging_checkbox.clicked.connect(self.on_debugging_checkbox_click)
        self.hide_names_checkbox.clicked.connect(self.on_hide_names_checkbox_click)
        self.flip_names_checkbox.clicked.connect(self.on_flip_names_checkbox_click)
        self.outline_values_checkbox.clicked.connect(self.on_outline_values_checkbox_click)
        self.save_path_button.clicked.connect(self.on_save_path_button_click)
        self.search_updates_button.clicked.connect(self.on_search_updates_button_click)

        settings_layout.addRow(QtWidgets.QLabel("Paskutinė rankiniu būdu analizuota vieta:"), self.last_dir_label)
        settings_layout.addRow(QtWidgets.QLabel("Kūrėjo režimas:"), self.debugging_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Demonstracinis režimas:"), self.hide_names_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Apversti vardus (grafikuose):"), self.flip_names_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Rodyti kontūrus (grafikų vertėse):"), self.outline_values_checkbox)
        settings_layout.addRow(QtWidgets.QLabel("Programos duomenys:"), self.save_path_button)
        if sys.platform == "win32":
            settings_layout.addRow(QtWidgets.QLabel("Ieškoti programos atnaujinimų:"), self.search_updates_button)

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

    def on_search_updates_button_click(self) -> None:
        self.update_check_worker = CheckForUpdatesWorker(self.app)
        self.update_check_thread = QtCore.QThread()
        self.update_check_worker.moveToThread(self.update_check_thread)

        def err(error_msg: str):
            self.update_check_thread.quit()
            self.app.show_error_box(error_msg)

        def ok(data: dict):
            self.update_check_thread.quit()

            maj_cur, min_cur, pat_cur = self.app.version
            maj_rem, min_rem, pat_rem = data["latest_version"]

            if maj_cur > maj_rem:
                return self.on_update_unavailable()

            if min_cur > min_rem:
                return self.on_update_unavailable()

            if pat_cur > pat_rem:
                return self.on_update_unavailable()

            if f'{maj_cur}.{min_cur}.{pat_cur}' == f'{maj_rem}.{min_rem}.{pat_rem}':
                return self.on_update_unavailable()

            self.on_update_available(data)

        # Connect signals
        self.update_check_worker.error.connect(err) # type: ignore
        self.update_check_worker.success.connect(ok) # type: ignore
        self.update_check_thread.started.connect(self.update_check_worker.search)

        self.update_check_thread.start()

    def on_update_unavailable(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Atnaujinimų nerasta", "Nerasta jokių programos atnaujinimų.",
            QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton
        )

    def on_update_available(self, data: dict) -> None:
        res = QtWidgets.QMessageBox.question(
            self, "Rastas atnaujinimas", "Rastas programos atnaujinimas. Ar norite jį atsisiųsti?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )
        
        if res == QtWidgets.QMessageBox.Yes:
            if platform.architecture()[0] == "64bit":
                url = data["url_win64"]
            else:
                url = data["url_win32"]
            webbrowser.open(url)

    def load_state(self) -> None:
        self.last_dir_label.setText(self.app.settings.last_dir or "nėra")
        self.debugging_checkbox.setChecked(self.app.settings.debugging)
        self.hide_names_checkbox.setChecked(self.app.settings.hide_names)
        self.flip_names_checkbox.setChecked(self.app.settings.flip_names)
        self.outline_values_checkbox.setChecked(self.app.settings.outlined_values)

    def save_state(self) -> None:
        self.unsaved = False
        self.app.settings.last_ver = list(self.app.version)
        self.app.settings.save()
        self.app.change_stack(self.app.MAIN_WIDGET)