from time import perf_counter

from PySide6.QtCore import QObject, QTimer


class IncrementalBuilder(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self._steps = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._advance)

    def start(self, steps):
        self.cancel()
        self._steps = iter(steps)
        self._timer.start(0)

    def cancel(self):
        self._timer.stop()
        if self._steps is not None:
            self._steps.close()
            self._steps = None

    def finish(self):
        self._timer.stop()
        try:
            while self._steps is not None:
                next(self._steps)
        except StopIteration:
            self._steps = None
        except Exception:
            self.cancel()
            raise

    def _advance(self):
        deadline = perf_counter() + 0.004
        try:
            while self._steps is not None and perf_counter() < deadline:
                next(self._steps)
        except StopIteration:
            self._steps = None
        except Exception:
            self.cancel()
            raise
        if self._steps is not None:
            self._timer.start(1)
