import sys
import signal
import warnings

from analyser.settings import Settings
from analyser.ui.app import App
from analyser.ui.qt_compat import QtWidgets

signal.signal(signal.SIGINT, signal.SIG_DFL)
warnings.filterwarnings("ignore", category=DeprecationWarning) 

if __name__ == "__main__":
    settings = Settings()
    settings.load()
    app = QtWidgets.QApplication(sys.argv)
    ex = App(settings)
    sys.excepthook = ex.excepthook
    sys.exit(app.exec_())
