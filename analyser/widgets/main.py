from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from analyser.qt_compat import QtWidgets, Qt

REPO_URL = "https://mokytojams.svetikas.lt/"

logger = logging.getLogger("analizatorius")

if TYPE_CHECKING:
    from analyser.app import App

class MainWidget(QtWidgets.QWidget):

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

        layout = QtWidgets.QVBoxLayout()
        
        manual_upload_button = QtWidgets.QPushButton("Įkelti ataskaitas rankiniu būdu (failai)")
        auto_upload_button = QtWidgets.QPushButton("Įkelti ataskaitas iš Mano Dienyno sistemos automatiškai")
        settings_button = QtWidgets.QPushButton("Nustatymai")
        notice_label = QtWidgets.QLabel()

        manual_upload_button.clicked.connect(self.on_manual_upload_button_click)
        auto_upload_button.clicked.connect(self.on_auto_upload_button_click)
        settings_button.clicked.connect(self.on_settings_button_click)

        major, minor, patch, build = app.version
        notice_label.setText(f"<a href=\"{REPO_URL}\">v{major}.{minor}.{patch}.{build} Dominykas Svetikas © 2022</a>")
        notice_label.setTextFormat(Qt.RichText)
        notice_label.setTextInteractionFlags(Qt.TextBrowserInteraction) # type: ignore
        notice_label.setOpenExternalLinks(True)

        # God forbid I have to mess with this sh*t again
        # Took longer than aligning a div in CSS
        layout.addWidget(manual_upload_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(auto_upload_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(settings_button, alignment=Qt.AlignVCenter) # type: ignore
        layout.addWidget(notice_label, alignment=Qt.AlignRight | Qt.AlignBottom | Qt.AlignJustify) # type: ignore
        self.setLayout(layout)

    def on_settings_button_click(self) -> None:
        self.app.settings_widget.load_state()
        self.app.set_window_title("Nustatymai")
        self.app.change_stack(self.app.SETTINGS_WIDGET)

    def on_manual_upload_button_click(self) -> None:
        self.app.set_window_title("Rankinis įkėlimas")
        self.app.change_stack(self.app.FILE_SELECTOR_WIDGET)

    def on_auto_upload_button_click(self) -> None:
        if self.app.client.is_logged_in:
            self.app.set_window_title("Vartotojo tipas")
            return self.app.change_stack(self.app.ROLE_SELECTOR_WIDGET)
        
        self.app.login_widget.clear_fields()
        self.app.login_widget.fill_fields()
        self.app.set_window_title("Prisijungimas")
        self.app.change_stack(self.app.LOGIN_WIDGET)
