from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication


class WindowActivationController(QObject):
    def __init__(self, app, window):
        super().__init__(window)
        self._window = window
        app.installEventFilter(self)
        app.applicationStateChanged.connect(self._state_changed)

    def eventFilter(self, watched, event):
        if watched is QApplication.instance() and event.type() == QEvent.Type.ApplicationActivate:
            self._restore_window()
        return False

    def _state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self._restore_window()

    def _restore_window(self):
        if self._window.isMinimized():
            self._window.setWindowState(
                self._window.windowState() & ~Qt.WindowState.WindowMinimized)
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
