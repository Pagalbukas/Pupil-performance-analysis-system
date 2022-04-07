import sys

from PySide6.QtWidgets import QApplication

from app import App
from files import copy_config_to_data
from settings import Settings

if __name__ == "__main__":
    copy_config_to_data()
    settings = Settings()
    app = QApplication(sys.argv)
    ex = App(settings)
    sys.exit(app.exec())
