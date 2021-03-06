import sys
import warnings

from analyser.app import App
from analyser.qt_compat import QtWidgets
from analyser.settings import Settings

warnings.filterwarnings("ignore", category=DeprecationWarning) 

if __name__ == "__main__":
    settings = Settings()
    app = QtWidgets.QApplication(sys.argv)
    ex = App(settings)
    sys.exit(app.exec_())
