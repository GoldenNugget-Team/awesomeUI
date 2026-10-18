"""Run bounded local archive work without blocking the Qt event loop."""
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from src.gui.theme import ColorThemeManager, t


class _FileThread(QThread):
    def __init__(self, callback, parent):
        super().__init__(parent)
        self.callback, self.result, self.error = callback, None, None

    def run(self):
        try:
            self.result = self.callback()
        except Exception as exc:
            self.error = exc


class _FileTaskDialog(QDialog):
    def __init__(self, parent, title, callback):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title, self))
        bar = QProgressBar(self)
        bar.setRange(0, 0)
        layout.addWidget(bar)
        self.worker = _FileThread(callback, self)
        self.worker.finished.connect(self.accept)
        ColorThemeManager.instance().theme_changed.connect(self._retheme)
        self._retheme()

    def _retheme(self):
        self.setStyleSheet(t('confirm_dialog'))

    def reject(self):
        if not self.worker.isRunning():
            super().reject()

    def closeEvent(self, event):
        if self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)


def run_file_task(parent, title, callback):
    dialog = _FileTaskDialog(parent, title, callback)
    dialog.worker.start()
    dialog.exec()
    dialog.worker.wait()
    result, error = dialog.worker.result, dialog.worker.error
    dialog.deleteLater()
    if error is not None:
        raise error
    return result
