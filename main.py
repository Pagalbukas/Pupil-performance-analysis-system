import sys

from PySide6.QtWidgets import QApplication
from app import App
from settings import Settings

if __name__ == "__main__":
    settings = Settings()
    app = QApplication(sys.argv)
    ex = App(settings)
    sys.exit(app.exec())
