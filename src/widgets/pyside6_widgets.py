"""Reusable PySide6 widgets.

The module intentionally has no imports from the original application. Copy this
file into another project and import the classes directly.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    """A simple rounded container with optional title and subtitle."""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            "QFrame#Card { background: #20242b; border: 1px solid #343a46; "
            "border-radius: 12px; }"
            "QLabel { color: #f5f7fa; background: transparent; }"
            "QLabel#CardSubtitle { color: #a8b0bd; }"
        )
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(6)
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            self.body.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("CardSubtitle")
            self.body.addWidget(self.subtitle_label)

    def add_widget(self, widget: QWidget) -> QWidget:
        """Append a widget and return it, which is convenient in fluent layouts."""
        self.body.addWidget(widget)
        return widget


class StatusBadge(QLabel):
    """Compact status label with a consistent semantic color."""

    COLORS = {
        "success": ("#b7f7ce", "#173c28"),
        "warning": ("#ffe4a8", "#4d3510"),
        "error": ("#ffc1c1", "#4c1f25"),
        "info": ("#c5dcff", "#1d3557"),
    }

    def __init__(
        self,
        text: str,
        kind: str = "info",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        foreground, background = self.COLORS.get(kind, self.COLORS["info"])
        self.setStyleSheet(
            f"color: {foreground}; background: {background}; padding: 3px 8px; "
            "border-radius: 8px; font-weight: 600;"
        )


class SearchField(QLineEdit):
    """Search field that emits only after the user pauses typing."""

    searchChanged = Signal(str)

    def __init__(self, placeholder: str = "Search…", delay_ms: int = 250, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(0, delay_ms))
        self.textChanged.connect(self._restart_timer)
        self._timer.timeout.connect(lambda: self.searchChanged.emit(self.text()))

    def _restart_timer(self) -> None:
        self._timer.start()


class LoadingButton(QPushButton):
    """Button with a built-in busy state; no spinner dependency is required."""

    clickedWhileReady = Signal()

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._label = text
        self._busy = False
        self.clicked.connect(self._emit_if_ready)

    @property
    def is_loading(self) -> bool:
        return self._busy

    def set_loading(self, loading: bool, label: str = "Working…") -> None:
        self._busy = loading
        self.setEnabled(not loading)
        self.setText(label if loading else self._label)

    def _emit_if_ready(self) -> None:
        if not self._busy:
            self.clickedWhileReady.emit()


class EmptyState(QWidget):
    """Centered empty state with an optional action button."""

    actionRequested = Signal()

    def __init__(
        self,
        title: str,
        message: str = "",
        action_text: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        if message:
            message_label = QLabel(message)
            message_label.setStyleSheet("color: #8f99a8;")
            message_label.setWordWrap(True)
            message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(message_label)
        if action_text:
            action = QPushButton(action_text)
            action.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            action.clicked.connect(self.actionRequested)
            layout.addWidget(action, alignment=Qt.AlignmentFlag.AlignCenter)


class Toast(QFrame):
    """Non-blocking notification that disappears automatically."""

    def __init__(self, message: str, timeout_ms: int = 2500, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 8, 9)
        label = QLabel(message)
        label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(label)
        close = QToolButton()
        close.setText("×")
        close.setStyleSheet("color: #cbd5e1; background: transparent; border: 0;")
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.setStyleSheet("QFrame { background: #171a20; border: 1px solid #414957; "
                           "border-radius: 10px; }")
        QTimer.singleShot(max(0, timeout_ms), self.close)

    @classmethod
    def show_message(cls, parent: QWidget, message: str, timeout_ms: int = 2500) -> "Toast":
        toast = cls(message, timeout_ms, parent)
        toast.adjustSize()
        margin = 18
        toast.move(parent.width() - toast.width() - margin, margin)
        toast.show()
        toast.raise_()
        return toast

