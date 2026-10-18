"""Read-only help for a registry tweak; opening it never changes selections."""
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QScrollArea, QWidget

from src.gui.theme import ColorThemeManager, t
from src.tweaks.registry import Kind


class TweakInfoDialog(QDialog):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        tr = lambda text: QCoreApplication.translate("Nugget", text)
        title = tr(spec.title)
        self.setWindowTitle(title)
        self.resize(520, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        scroll = QScrollArea(self)
        self._scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        self._content = content
        content.setObjectName("tweakInfoContent")
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 8, 0)
        body.setSpacing(14)

        def label(text, name="confirmRow"):
            widget = QLabel(text, content)
            widget.setTextFormat(Qt.PlainText)
            widget.setWordWrap(True)
            widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            widget.setObjectName(name)
            body.addWidget(widget)

        label(title, "confirmTitle")
        label(tr(spec.description) if spec.description else
              tr("No detailed description is available for this tweak yet."))
        requirements = []
        if spec.min_version:
            requirements.append(tr("Minimum iOS version: {0}").format(spec.min_version))
        if spec.max_version:
            requirements.append(tr("Maximum iOS version: {0}").format(spec.max_version))
        if spec.iphone_only:
            requirements.append(tr("iPhone only"))
        if spec.ipad_only:
            requirements.append(tr("iPad only"))
        label(tr("Compatibility"), "confirmTitle")
        label("\n".join(requirements) if requirements else
              tr("No additional version or device restrictions are listed for this tweak."))
        if spec.kind == Kind.NUMBER:
            label(tr("Range: {0} – {1}").format(f"{spec.min_value:g}", f"{spec.max_value:g}"))
        label(tr("How to restore defaults"), "confirmTitle")
        label(tr("Turning off a tweak only removes it from the next apply. "
                 "To restore original values, open Apply, choose Restore Defaults, "
                 "and select the relevant tweak page."), "confirmMuted")
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        close = QPushButton(tr("Close"), self)
        close.setObjectName("cancelBtn")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        ColorThemeManager.instance().theme_changed.connect(self._retheme)
        self._retheme()

    def _retheme(self):
        self.setStyleSheet(t("confirm_dialog"))
        self._scroll.setStyleSheet(t("tweak_info_scroll"))
