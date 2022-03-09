import os

from PyQt5.QtWidgets import QWidget, QFileDialog
from typing import List

from settings import Settings

class App(QWidget):

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.title = 'Mokinių pasiekimų analizatorius'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

    def ask_files_dialog(self) -> List[str]:
        directory = self.settings.last_dir
        if directory is None or not os.path.exists(directory):
            directory = os.path.join(os.environ["userprofile"], "Downloads")

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pasirinkite Excel suvestinių failus",
            directory,
            "Excel suvestinių failai (*.xlsx *.xls)"
        )

        # Store the last dir in the settings
        if len(files) > 0:
            self.settings.last_dir = os.path.dirname(files[0])
            self.settings.save()
        return files
