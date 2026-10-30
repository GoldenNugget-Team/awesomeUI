"""Apply large list filters without blocking input or relaying out every row."""
from time import perf_counter

from PySide6.QtCore import QObject, QTimer


class VisibilityBatch(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1)
        self._timer.timeout.connect(self._advance)
        self._target = None
        self._operations = []
        self._offset = 0

    def cancel(self, *_args):
        self._timer.stop()
        self._release()
        self._operations = []

    def apply(self, target, operations):
        self.cancel()
        self._operations = [(widget, shown) for widget, shown in operations
                            if widget.isHidden() == shown]
        if not self._operations:
            return
        self._offset = 0
        self._target = target
        self._layout_enabled = target.layout().isEnabled()
        self._updates_enabled = target.updatesEnabled()
        target.layout().setEnabled(False)
        target.setUpdatesEnabled(False)
        if not target.isVisible():
            for widget, shown in self._operations:
                widget.setVisible(shown)
            self.cancel()
        else:
            self._timer.start()

    def _advance(self):
        deadline = perf_counter() + 0.004
        count = 0
        while self._offset < len(self._operations):
            widget, shown = self._operations[self._offset]
            widget.setVisible(shown)
            self._offset += 1
            count += 1
            if count >= 24 or perf_counter() >= deadline:
                break
        if self._offset == len(self._operations):
            self.cancel()

    def _release(self):
        if self._target is None:
            return
        target, self._target = self._target, None
        target.layout().setEnabled(self._layout_enabled)
        target.setUpdatesEnabled(self._updates_enabled)
        target.updateGeometry()
