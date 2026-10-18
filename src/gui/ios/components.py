from PySide6.QtCore import (
    Qt, QCoreApplication, Signal as pyqtSignal, QSize, QRectF,
    QPropertyAnimation, QEasingCurve, Property, QEvent,
)
from PySide6.QtGui import QPainter, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy, QDialog, QDialogButtonBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QVBoxLayout, QScrollArea, QButtonGroup, QToolButton,
)

from src.gui.theme import t, ColorThemeManager, theme_pixmap
from src.gui.theme.theme_manager import connect_visible_theme


def _auto_retheme(widget):
    """Connect a widget's ``_retheme`` to the global theme_changed signal."""
    connect_visible_theme(widget)


class TextInputDialog(QDialog):
    """iOS-style text input dialog."""
    def __init__(self, title: str, current_value: str = "", parent=None):
        super().__init__(parent)
        ColorThemeManager.instance().theme_changed.connect(self._retheme)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)
        self._retheme()

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        self.input = QLineEdit()
        self.input.setText(current_value)
        self.input.setAccessibleName(title)
        self.input.setPlaceholderText(QCoreApplication.translate("TextInputDialog", "Enter value..."))
        layout.addWidget(self.input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet(t("text_input_dialog"))
        layout.addWidget(buttons)

    def _retheme(self):
        self.setStyleSheet(t("text_input_dialog"))

    def showEvent(self, event):
        super().showEvent(event)
        self.input.setFocus(Qt.OtherFocusReason)

    def get_value(self) -> str:
        return self.input.text()


def decimals_for_step(step) -> int:
    """Decimal places needed to express ``step`` (0.5 -> 1, 1 -> 0, 0.25 -> 2)."""
    try:
        text = f"{float(step):.6f}".rstrip("0")
    except (TypeError, ValueError):
        return 0
    if text.endswith("."):
        return 0
    return len(text.split(".", 1)[1])


class NumberInputDialog(QDialog):
    """iOS-style number input dialog.

    ``step`` picks the widget: an integral step keeps the integer spin box
    (every existing numeric tweak), a finer one switches to a decimal box so
    values like 0.5 are expressible. ``get_value`` returns an int in the
    integral case and a float otherwise.
    """
    def __init__(self, title: str, current_value: int = 0, min_val: int = 0, max_val: int = 999,
                 parent=None, step: float = 1.0):
        super().__init__(parent)
        ColorThemeManager.instance().theme_changed.connect(self._retheme)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)
        self._retheme()

        self._decimals = decimals_for_step(step)
        self._integral = self._decimals == 0

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        if self._integral:
            self.spin = QSpinBox()
            self.spin.setRange(int(min_val), int(max_val))
            self.spin.setValue(int(current_value))
            self.spin.setButtonSymbols(QSpinBox.NoButtons)
        else:
            self.spin = QDoubleSpinBox()
            self.spin.setDecimals(self._decimals)
            self.spin.setSingleStep(abs(float(step)))
            self.spin.setRange(float(min_val), float(max_val))
            self.spin.setValue(float(current_value))
            self.spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin.setStyleSheet(t('number_input_field'))
        layout.addWidget(self.spin)
        if not self._integral:
            hint = QLabel(QCoreApplication.translate("Nugget", "Range: {0} – {1} · Step: {2}").format(
                self.spin.locale().toString(float(min_val), 'f', self._decimals),
                self.spin.locale().toString(float(max_val), 'f', self._decimals),
                self.spin.locale().toString(float(step), 'f', self._decimals)))
            hint.setWordWrap(True)
            hint.setStyleSheet(t("home_subtitle"))
            layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _retheme(self):
        self.setStyleSheet(t('number_input_dialog'))
        if hasattr(self, 'spin'):
            self.spin.setStyleSheet(t('number_input_field'))

    def showEvent(self, event):
        super().showEvent(event)
        self.spin.setFocus(Qt.OtherFocusReason)
        self.spin.selectAll()

    def get_value(self):
        self.spin.interpretText()
        value = self.spin.value()
        return int(value) if self._integral else round(float(value), self._decimals)


class IOSSummaryDialog(QDialog):
    """iOS-style confirm dialog listing what an action will do.

    Built for the pre-apply summary: takes a title, a list of ``lines`` and an
    optional muted footer note, then offers Cancel / a themed confirm button.
    ``exec()`` returns ``QDialog.Accepted`` when the user confirms.

    An optional ``extra_button`` (e.g. "Update Cache") renders as an
    additional themed button that returns ``extra_result`` (default 2) so the
    caller can branch on it without closing with a plain confirm.
    """
    def __init__(self, title: str, lines: list[str], muted: str = "",
                 confirm_text: str = "", extra_button: str = "",
                 extra_result: int = 2, parent=None, details_callback=None,
                 header_widget=None, acknowledge_text: str = "", preview_callback=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(140)
        _auto_retheme(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title_lbl = QLabel(title, self)
        title_lbl.setObjectName("confirmTitle")
        title_lbl.setWordWrap(True)
        header = QHBoxLayout()
        self._summary_icon = QLabel(self)
        self._summary_icon.setFixedSize(36, 36)
        header.addWidget(self._summary_icon)
        header.addWidget(title_lbl, 1)
        layout.addLayout(header)
        if header_widget is not None:
            header_widget.setParent(self)
            layout.addWidget(header_widget)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        summary = IOSCard()
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(12)
        for line in lines:
            row_lbl = QLabel(line, self)
            row_lbl.setObjectName("confirmRow")
            row_lbl.setWordWrap(True)
            summary_layout.addWidget(row_lbl)
        scroll.setWidget(summary)
        scroll.setMinimumHeight(140)
        scroll.setMaximumHeight(320)
        layout.addWidget(scroll, 1)

        if muted:
            muted_lbl = QLabel(muted, self)
            muted_lbl.setObjectName("confirmMuted")
            muted_lbl.setWordWrap(True)
            layout.addWidget(muted_lbl)

        layout.addStretch()

        secondary = QHBoxLayout()
        secondary.setSpacing(12)
        for text, callback in ((QCoreApplication.translate("ApplyPreview", "View changes"), details_callback),
                               (QCoreApplication.translate("DeviceTwin", "Preview on iPhone"), preview_callback)):
            if callback is None:
                continue
            button = QPushButton(text, self)
            button.setObjectName("cancelBtn")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, cb=callback: cb(self))
            secondary.addWidget(button)
        if secondary.count():
            layout.addLayout(secondary)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        if extra_button:
            extra_btn = QPushButton(extra_button, self)
            extra_btn.setObjectName("cancelBtn")
            extra_btn.setCursor(Qt.PointingHandCursor)
            extra_btn.clicked.connect(lambda: self.done(extra_result))
            buttons.addWidget(extra_btn)
        cancel_btn = QPushButton(QCoreApplication.translate("IOSSummaryDialog", "Cancel"), self)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        self.confirm_btn = QPushButton(
            confirm_text or QCoreApplication.translate("IOSSummaryDialog", "Confirm"), self)
        self.confirm_btn.setObjectName("confirmBtn")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        buttons.addWidget(self.confirm_btn)
        # A checkbox the user must tick before confirming (e.g. high risk).
        self.acknowledge = None
        if acknowledge_text:
            from PySide6.QtWidgets import QCheckBox
            self.acknowledge = QCheckBox(acknowledge_text, self)
            self.confirm_btn.setEnabled(False)
            self.confirm_btn.setDefault(False)
            cancel_btn.setDefault(True)
            self.acknowledge.toggled.connect(self.confirm_btn.setEnabled)
            layout.addWidget(self.acknowledge)
        layout.addLayout(buttons)
        for button in self.findChildren(QPushButton):
            button.setMinimumHeight(48)
        self._retheme()

    def _retheme(self):
        self.setStyleSheet(t("confirm_dialog") + t("summary_dialog"))
        from src.gui.ios.feature_icons import FEATURE_ICONS
        self._summary_icon.setPixmap(theme_pixmap(
            FEATURE_ICONS["Tweaks"], ColorThemeManager.instance().colors.text_primary,
            36, self.devicePixelRatioF()))


class IOSSearchField(QLineEdit):
    """Local, case-insensitive list filter with a clear button."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(QCoreApplication.translate("ListSearch", "Search this list…"))
        self.setAccessibleName(self.placeholderText())
        self.setClearButtonEnabled(False)
        self.setFixedHeight(44)
        self.setTextMargins(34, 0, 38, 0)
        self._clear_button = QToolButton(self)
        self._clear_button.setFixedSize(36, 36)
        self._clear_button.setIconSize(QSize(18, 18))
        self._clear_button.setCursor(Qt.PointingHandCursor)
        self._clear_button.setAccessibleName(QCoreApplication.translate("ListSearch", "Clear search"))
        self._clear_button.setToolTip(QCoreApplication.translate("ListSearch", "Clear search"))
        self._clear_button.clicked.connect(self._clear_search)
        self.textChanged.connect(lambda text: self._clear_button.setVisible(bool(text)))
        self._clear_button.hide()
        self._search_icon = QLabel(self)
        self._search_icon.setFixedSize(20, 20)
        self._search_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._search_icon.setStyleSheet("background: transparent; border: none; padding: 0;")
        self._retheme()
        _auto_retheme(self)

    def _clear_search(self):
        self.clear()
        self.setFocus(Qt.OtherFocusReason)

    def matches(self, *texts):
        haystack = " ".join(texts).casefold()
        return all(word in haystack for word in self.text().casefold().split())

    def _retheme(self):
        self.setStyleSheet(t("list_search"))
        colors = ColorThemeManager.instance().colors
        self._clear_button.setIcon(QIcon(theme_pixmap(
            ":/icon/x-lg.svg", colors.text_secondary, 18, self.devicePixelRatioF())))
        self._clear_button.setStyleSheet(t("search_clear_button"))
        self._search_icon.setPixmap(theme_pixmap(
            ":/icon/search.svg", ColorThemeManager.instance().colors.text_secondary,
            20, self.devicePixelRatioF()))
        self._search_icon.move(14, (self.height() - 20) // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._search_icon.move(14, (self.height() - 20) // 2)
        self._clear_button.move(self.width() - 44, (self.height() - 36) // 2)


class IOSSegmentedFilter(QWidget):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setObjectName("iosSegmentedFilter")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(44)
        self._items = items
        self._index = 0
        self._group = QButtonGroup(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        for index, (title, data) in enumerate(items):
            button = QPushButton(title, self)
            button.setCheckable(True)
            button.setFixedHeight(34)
            button.setCursor(Qt.PointingHandCursor)
            self._group.addButton(button, index)
            layout.addWidget(button)
        self._group.button(0).setChecked(True)
        self._group.idClicked.connect(self.setCurrentIndex)
        self._retheme()
        _auto_retheme(self)

    def currentData(self):
        return self._items[self._index][1]

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, index):
        if index == self._index or not 0 <= index < len(self._items):
            return
        self._index = index
        self._group.button(index).setChecked(True)
        self.currentIndexChanged.emit(index)

    def _retheme(self):
        self.setStyleSheet(t("segmented_filter"))


class IOSSearchEmpty(QLabel):
    def __init__(self, parent=None):
        super().__init__(QCoreApplication.translate("ListSearch", "No matches found."), parent)
        self.setWordWrap(True)
        self.hide()
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("list_search_empty"))


class IOSSectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("iosSectionHeader")
        self.setProperty("cls", "iosSectionHeader")
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("section_header"))


class IOSCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("iosCard")
        self.setFrameShape(QFrame.StyledPanel)
        self._retheme()
        _auto_retheme(self)
        # Don't create a default layout - let the caller decide

    def _retheme(self):
        self.setStyleSheet(t("card"))


class IOSCollapsibleSection(QWidget):
    """A section header that expands/collapses the content block below it.

    Callers add their widgets to ``self.body_layout`` after construction (a
    tweak section is rendered straight from the registry, so the body is
    filled in right after this widget is created) and read back the resulting
    state through ``expanded`` / the ``toggled`` signal.
    """

    EXPANDED_CHEVRON = "\u25bc"    # down-pointing disclosure marker
    COLLAPSED_CHEVRON = "\u25b6"   # right-pointing disclosure marker

    toggled = pyqtSignal(bool)

    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("iosCollapsibleSection")
        self._title = title
        self._title_suffix = ""
        self._expanded = bool(expanded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QPushButton(self)
        self.header.setObjectName("iosCollapsibleHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setCheckable(True)
        self.header.setFocusPolicy(Qt.NoFocus)
        self.header.clicked.connect(self.toggle)
        layout.addWidget(self.header)

        self.body = QWidget(self)
        self.body.setObjectName("iosCollapsibleBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)
        layout.addWidget(self.body)

        # No toggled() emission here: the state was handed in by the caller.
        self.set_expanded(self._expanded)
        self._retheme()
        _auto_retheme(self)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool):
        """Show/hide the body. Only emits ``toggled`` on an actual change."""
        expanded = bool(expanded)
        changed = expanded != self._expanded
        self._expanded = expanded
        self.header.setChecked(expanded)
        self._update_header_text()
        self.body.setVisible(expanded)
        if changed:
            self.toggled.emit(expanded)

    def set_title_suffix(self, suffix: str):
        """Append a compact status/count suffix to the section title."""
        self._title_suffix = str(suffix or "")
        self._update_header_text()

    def _update_header_text(self):
        self.header.setText(
            f"{self.EXPANDED_CHEVRON if self._expanded else self.COLLAPSED_CHEVRON}"
            f"  {self._title}{self._title_suffix}")

    def toggle(self):
        self.set_expanded(not self._expanded)

    def _retheme(self):
        self.header.setStyleSheet(t("collapsible_header"))


class IOSNavBar(QWidget):
    """Page identity, actions, and section navigation in one persistent header."""

    def __init__(self, title="", on_back=None, right_action=None,
                 window=None, parent=None):
        super().__init__(parent)
        self.setObjectName("iosNavBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._on_back = on_back or getattr(window, "_go_back", None)
        self._icon_path = None
        self._category_buttons = []
        self._right_btn = None
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.back_btn = QPushButton("‹", self)
        self.back_btn.setFixedSize(36, 36)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setToolTip(QCoreApplication.translate("Nugget", "Back"))
        self.back_btn.setAccessibleName(self.back_btn.toolTip())
        self.back_btn.clicked.connect(self._handle_back)
        row.addWidget(self.back_btn)
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setFixedSize(32, 32)
        self.icon_lbl.hide()
        row.addWidget(self.icon_lbl)
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(self.title_lbl, 1)
        self._right_box = QWidget(self)
        self._right_layout = QHBoxLayout(self._right_box)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._right_box)
        root.addLayout(row)
        self._categories = QScrollArea(self)
        self._categories.setWidgetResizable(True)
        self._categories.setFrameShape(QFrame.NoFrame)
        self._categories.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._categories.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._categories.setFixedHeight(44)
        self._category_content = QWidget()
        self._category_layout = QHBoxLayout(self._category_content)
        self._category_layout.setContentsMargins(0, 0, 0, 0)
        self._category_layout.setSpacing(6)
        self._categories.setWidget(self._category_content)
        self._categories.viewport().installEventFilter(self)
        self._category_content.installEventFilter(self)
        root.addWidget(self._categories)
        self._categories.hide()
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("nav_bar"))
        self.back_btn.setStyleSheet(t("nav_back_btn"))
        self.title_lbl.setStyleSheet(t("nav_title"))
        self._categories.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        if self._icon_path:
            self.icon_lbl.setPixmap(theme_pixmap(
                self._icon_path, ColorThemeManager.instance().colors.text_primary,
                28, self.devicePixelRatioF()))
        for button in self._category_buttons:
            button.setStyleSheet(t("nav_category"))
        if self._right_btn:
            self._right_btn.setStyleSheet(t("nav_right_btn"))

    def set_title(self, title):
        self.title_lbl.setText(title)

    def set_icon(self, resource_path):
        self._icon_path = resource_path
        self.icon_lbl.setVisible(bool(resource_path))
        self._retheme()

    def set_categories(self, categories):
        while self._category_layout.count():
            item = self._category_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._category_buttons = []
        self._categories.setVisible(len(categories) > 1)
        for title, callback in categories if len(categories) > 1 else []:
            button = QPushButton(title.replace("&", "&&"), self._category_content)
            button.setAccessibleName(title)
            button.installEventFilter(self)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(32)
            button.setStyleSheet(t("nav_category"))
            button.setFixedWidth(button.sizeHint().width())
            button.clicked.connect(
                lambda checked=False, b=button, cb=callback: self._jump(b, cb))
            self._category_layout.addWidget(button)
            self._category_buttons.append(button)
        self._category_layout.addStretch(1)
        width = sum(button.width() for button in self._category_buttons)
        width += max(0, len(self._category_buttons) - 1) * 6
        self._category_content.setMinimumWidth(width)
        self.setFixedHeight(108 if len(categories) > 1 else 64)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Wheel:
            bar = self._categories.horizontalScrollBar()
            if bar.maximum() > 0:
                pixels = event.pixelDelta()
                angles = event.angleDelta()
                delta = pixels.x() or pixels.y()
                if not delta:
                    delta = (angles.x() or angles.y()) / 120 * 64
                if delta:
                    bar.setValue(bar.value() - round(delta))
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def _jump(self, selected, callback):
        for button in self._category_buttons:
            button.setChecked(button is selected)
        callback()

    def set_back_visible(self, visible):
        self.back_btn.setVisible(visible)

    def set_right_action(self, label_text, callback):
        self._clear_right()
        button = QPushButton(label_text, self)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(t("nav_right_btn"))
        button.clicked.connect(callback)
        self._right_layout.addWidget(button)
        self._right_btn = button

    def clear_right_action(self):
        self._clear_right()

    def _clear_right(self):
        if self._right_btn is not None:
            self._right_layout.removeWidget(self._right_btn)
            self._right_btn.deleteLater()
            self._right_btn = None

    def _handle_back(self):
        if self._on_back:
            self._on_back()


class IOSValueRow(QPushButton):
    """Editable setting with a wrapping title and a separate visible value."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._title = title
        self.setObjectName("iosValueRow")
        self.setCursor(Qt.PointingHandCursor)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setMinimumHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(12)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("valueRowTitle")
        self.value_label = QLabel(self)
        self.value_label.setObjectName("valueRowValue")
        for label in (self.title_label, self.value_label):
            label.setWordWrap(True)
            label.setTextFormat(Qt.PlainText)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            text.addWidget(label)
        layout.addLayout(text, 1)
        arrow = QLabel("›", self)
        arrow.setObjectName("valueRowArrow")
        arrow.setFixedSize(20, 28)
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(arrow)
        self.set_display_value(QCoreApplication.translate("Nugget", "Not set"))
        self._retheme()
        _auto_retheme(self)

    def sizeHint(self):
        return self.layout().sizeHint().expandedTo(QSize(0, 56))

    def minimumSizeHint(self):
        return QSize(0, 56)

    def heightForWidth(self, width):
        return max(56, self.layout().totalHeightForWidth(width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMinimumHeight(self.heightForWidth(self.width()))

    def set_display_value(self, value):
        self.value_label.setText(str(value))
        self.setMinimumHeight(self.heightForWidth(self.width()))
        self.updateGeometry()
        self.setAccessibleName(f"{self._title}: {value}")

    def _retheme(self):
        self.setStyleSheet(t("value_row"))


class IOSSettingsRow(QPushButton):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setObjectName("iosSettingsRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setText(f"{title}  ›")
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("settings_row"))


class IOSSettingsAction(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("settings_action"))


class IOSPrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("iosPrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("primary_button"))


class IOSDangerButton(QPushButton):
    """Red destructive CTA (Reset Tweaks / Remove Tweaks)."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("iosDangerButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self._retheme()
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("danger_button"))


class IOSSwitch(QPushButton):
    """iOS-style toggle switch: the track color fades while the knob slides.

    Track and knob are drawn in ``paintEvent`` (rather than a stylesheet plus a
    child ``QLabel``) so the knob can move on every animation frame without
    child-widget repaint artifacts. ``switch_progress`` runs 0.0 = off to
    1.0 = on and drives both the knob position and the track color.
    """

    TRACK_SIZE = QSize(51, 31)
    KNOB_SIZE = 27
    KNOB_INSET = 2
    ANIM_MS = 180
    KNOB_COLOR = QColor("#FFFFFF")

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(self.TRACK_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        self._progress = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"switch_progress", self)
        self._anim.setDuration(self.ANIM_MS)

        # set the state before connecting: building a page must not animate
        self.setChecked(checked)
        self.toggled.connect(self._on_toggled)
        _auto_retheme(self)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value):
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    switch_progress = Property(float, _get_progress, _set_progress)

    def _on_toggled(self, checked: bool):
        if not self.isVisible():
            # not on screen (page still being built): nothing to animate
            self._anim.stop()
            self._set_progress(1.0 if checked else 0.0)
            return
        self._animate_to(1.0 if checked else 0.0)

    def _animate_to(self, target: float):
        # restart from the current position, so rapid clicks blend instead of
        # snapping back to an end state
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(
            QEasingCurve.Type.OutCubic if target > self._progress
            else QEasingCurve.Type.InOutCubic)
        self._anim.start()

    def _retheme(self):
        # a theme change must not animate: stop and snap to the current state
        self._anim.stop()
        self._set_progress(1.0 if self.isChecked() else 0.0)

    def paintEvent(self, event):
        c = ColorThemeManager.instance().colors
        p = self._progress
        off = QColor(c.border)
        # A selected switch is an active control, so it follows the user's
        # chosen accent instead of the semantic success green.
        on = QColor(c.accent)
        track = QColor(
            round(off.red() + (on.red() - off.red()) * p),
            round(off.green() + (on.green() - off.green()) * p),
            round(off.blue() + (on.blue() - off.blue()) * p),
        )

        knob = float(self.KNOB_SIZE)
        inset = self.KNOB_INSET
        travel = self.width() - knob - 2 * inset
        knob_x = inset + travel * p

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(1.0 if self.isEnabled() else 0.45)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(
            QRectF(0, 0, self.width(), self.height()),
            self.height() / 2.0, self.height() / 2.0)
        painter.setBrush(self.KNOB_COLOR)
        painter.drawRoundedRect(
            QRectF(knob_x, inset, knob, knob), knob / 2.0, knob / 2.0)
        painter.end()


class IOSValueLabel(QLabel):
    """Label showing current value in parentheses"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._retheme()
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        _auto_retheme(self)

    def _retheme(self):
        self.setStyleSheet(t("value_label"))
