try:
    import PySide6.QtWidgets as _QtWidgets
    import PySide6.QtCore as _QtCore
    import PySide6.QtGui as _QtGui
    from PySide6.QtCore import Qt as _Qt
except ImportError:
    import PySide2.QtWidgets as _QtWidgets # type: ignore
    import PySide2.QtCore as _QtCore # type: ignore
    import PySide2.QtGui as _QtGui # type: ignore
    from PySide2.QtCore import Qt as _Qt # type: ignore

QtWidgets = _QtWidgets
QtCore = _QtCore
QtGui = _QtGui

Qt = _Qt
