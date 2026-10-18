from PySide6.QtCore import QCoreApplication, Qt, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QDialog, QLabel, QHBoxLayout, QPushButton
)

from src.gui.ios.components import (
    IOSCollapsibleSection, IOSCard, IOSValueRow,
    IOSSwitch, TextInputDialog, NumberInputDialog, decimals_for_step,
    IOSSearchField, IOSSearchEmpty, IOSSegmentedFilter,
)
from src.gui.ios.compat import device_family, is_tweak_compatible
from src.gui.theme import ColorThemeManager, t, theme_icon, theme_pixmap
from src.tweaks.tweaks import tweaks, TweakID
from src.tweaks.registry import SPECS_BY_SECTION, SECTION_FEATURES, Kind, Section
from src.tweaks.tweak_loader import load_plist_tweaks
from src.tweaks.hidden import current_hidden_feature_names, current_hidden_tweak_names

# Feature (page) name -> registry Section it maps to in the iOS tweaks UI.
# A HotLoad-hidden feature loses its whole section here (and the Sidebar/Home
# entries), so its tweaks are never even shown.
_SECTION_FEATURES = SECTION_FEATURES


def _hidden_feature_names() -> set:
    """Names of HotLoad-hidden features for the current setup, as a set."""
    return current_hidden_feature_names()


def _fmt_number(value) -> str:
    """Render a numeric tweak value compactly (5, 0.5, 1)."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _hidden_tweak_names() -> set:
    """Names of the tweaks that belong to HotLoad-hidden features for the
    current setup. Used by the preset loader to strip them during load."""
    return current_hidden_tweak_names()


def _hidden_sections() -> set:
    """Registry Sections whose feature is hidden, so we skip rendering them."""
    hidden = _hidden_feature_names()
    return {s for s, feat in _SECTION_FEATURES.items() if feat in hidden}


# Collapsed tweak sections are remembered per section name, so a rebuild (or a
# restart) comes back exactly as the user left it.
_COLLAPSED_KEY = "tweaks_collapsed_sections"


def _load_collapsed_sections() -> set:
    """Section names the user collapsed."""
    from src.controllers.settings import Settings
    raw = Settings("settings").value(_COLLAPSED_KEY, "", type=str) or ""
    return {part.strip() for part in str(raw).split(",") if part.strip()}


def _save_collapsed_section(name: str, collapsed: bool):
    from src.controllers.settings import Settings
    store = Settings("settings")
    names = _load_collapsed_sections()
    if collapsed:
        names.add(name)
    else:
        names.discard(name)
    store.setValue(_COLLAPSED_KEY, ",".join(sorted(names)))


class IOSSectionContent(QWidget):
    """iOS-style tweak controls for one or more registry sections.

    Can be reused inside any scroll area or page.
    """

    def __init__(self, window, sections=None, parent=None):
        super().__init__(parent)
        self.window = window
        self.sections = sections
        self._switch_labels = []
        self._solarium_visible: bool = None
        from src.controllers.favorites import TweakFavorites
        self._favorites = TweakFavorites.instance()

        # Load tweaks (idempotent) so the sections below actually populate
        load_plist_tweaks()

        # persistent root layout: keeps only a rebuildable inner widget
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.search = IOSSearchField(self)
        self.search.setPlaceholderText(QCoreApplication.translate("Nugget", "Search tweaks…"))
        self.search.setAccessibleName(self.search.placeholderText())
        self.filter_control = IOSSegmentedFilter([
            (QCoreApplication.translate("Nugget", "All"), "all"),
            (QCoreApplication.translate("Nugget", "Enabled"), "enabled"),
            (QCoreApplication.translate("Nugget", "Favorites"), "favorites"),
        ], self)
        self.filter_control.setAccessibleName(QCoreApplication.translate("Nugget", "Tweak filter"))
        search_row = QHBoxLayout()
        search_row.setContentsMargins(16, 16, 16, 0)
        search_row.setSpacing(8)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.filter_control)
        root.addLayout(search_row)
        self._inner = None

        self.rebuild()
        self.search.textChanged.connect(self._apply_search)
        self.filter_control.currentIndexChanged.connect(self._apply_search)
        self._favorites.changed.connect(self._refresh_favorites)
        ColorThemeManager.instance().theme_changed.connect(self._refresh_action_icons)

    def rebuild(self):
        """(Re)build the section controls for the currently selected device.

        Called once in ``__init__`` and again whenever the selected device
        changes, so per-device compatibility filtering (``min_version`` /
        ``iphone_only`` / ``ipad_only`` from the registry) and HotLoad-hiding
        are re-evaluated instead of being frozen at startup, when no device is
        known yet (that would wrongly hide e.g. the Dynamic Island tweaks).
        """
        # Tear down the previous build (widgets + layout) so the section can be
        # re-rendered in place from the single registry definition below.
        if self._inner is not None:
            self.layout().removeWidget(self._inner)
            self._inner.deleteLater()
            self._inner = None

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 32)
        layout.setSpacing(10)
        inner = QWidget(self)
        inner.setLayout(layout)
        self._inner = inner
        self.layout().addWidget(inner)

        self._switch_labels = []
        self._info_buttons = []
        self._favorite_buttons = {}
        self._search_rows = []
        self._search_sections = []
        self._search_expanded = {}
        self.force_solarium_fallback_card = None

        try:
            device_ver = self.window.device_manager.get_current_device_version()
        except Exception:
            device_ver = ""
        try:
            model = self.window.device_manager.get_current_device_model() or ""
        except Exception:
            model = ""
        is_iphone = device_family(model) == "iphone"

        def is_compatible(tweak_id: TweakID) -> bool:
            return is_tweak_compatible(tweak_id, device_ver, is_iphone, model)

        # Helper to create a switch row for boolean tweaks
        def make_switch(tweak_id: TweakID, title: str, description: str = "",
                        target: QVBoxLayout = None):
            if tweak_id not in tweaks:
                return
            tweak = tweaks[tweak_id]
            card = IOSCard()
            if tweak_id == TweakID.ForceSolariumFallback:
                self.force_solarium_fallback_card = card
            if not is_compatible(tweak_id):
                card.hide()
            row_layout = QHBoxLayout(card)
            row_layout.setContentsMargins(16, 12, 16, 12)
            row_layout.setSpacing(12)

            c = ColorThemeManager.instance().colors
            label = QLabel(title)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
            self._switch_labels.append(label)
            row_layout.addWidget(label, 1)
            switch = IOSSwitch(tweak.enabled)
            switch.toggled.connect(lambda checked: tweak.set_enabled(checked))
            row_layout.addWidget(switch)
            row_layout.addWidget(self._make_favorite_button(tweak_id, title))
            row_layout.addWidget(self._make_info_button(tweak_id, title))

            if description:
                label.setToolTip(description)
                switch.setToolTip(description)
                card.setToolTip(description)

            (target or layout).addWidget(card)
            self._search_rows.append((card, tweak_id, title, description, is_compatible(tweak_id)))

        # Helper for text input tweaks
        def make_text_input(tweak_id: TweakID, title: str, description: str = "",
                            target: QVBoxLayout = None):
            if tweak_id not in tweaks:
                return
            if not is_compatible(tweak_id):
                return
            tweak = tweaks[tweak_id]
            card = IOSCard()
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 8, 14, 8)
            card_layout.setSpacing(10)
            row = IOSValueRow(title)
            if description:
                row.setToolTip(description)
            current = ""
            if getattr(tweak, 'value', None) is not None:
                current = str(tweak.value)
                row.set_display_value(current if current else QCoreApplication.translate("Nugget", "Empty"))
            row.clicked.connect(lambda: self._show_text_input_dialog(tweak_id, title, current, row))
            card_layout.addWidget(row, 1)
            card_layout.addWidget(self._make_favorite_button(tweak_id, title))
            card_layout.addWidget(self._make_info_button(tweak_id, title))
            (target or layout).addWidget(card)
            self._search_rows.append((card, tweak_id, title, description, True))

        # Helper for number input tweaks
        def make_number_input(tweak_id: TweakID, title: str, min_val: int = 0, max_val: int = 999,
                              description: str = "", step: float = 1.0,
                              target: QVBoxLayout = None):
            if tweak_id not in tweaks:
                return
            if not is_compatible(tweak_id):
                return
            tweak = tweaks[tweak_id]
            card = IOSCard()
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 8, 14, 8)
            card_layout.setSpacing(10)
            row = IOSValueRow(title)
            if description:
                row.setToolTip(f"{description}\n\n"
                               + QCoreApplication.translate("Nugget", "Range: {0} – {1}")
                               .format(_fmt_number(min_val), _fmt_number(max_val)))
            decimals = decimals_for_step(step)
            current = 0
            if getattr(tweak, 'value', None) is not None:
                current = int(tweak.value) if decimals == 0 else float(tweak.value)
                row.set_display_value(_fmt_number(current))
            row.clicked.connect(lambda: self._show_number_input_dialog(
                tweak_id, title, current, row, min_val, max_val, step))
            card_layout.addWidget(row, 1)
            card_layout.addWidget(self._make_favorite_button(tweak_id, title))
            card_layout.addWidget(self._make_info_button(tweak_id, title))
            (target or layout).addWidget(card)
            self._search_rows.append((card, tweak_id, title, description, True))

        # Render sections straight from the registry. Titles (and descriptions)
        # are stored as QT_TRANSLATE_NOOP markers and translated here, at
        # render time.
        def tr_title(spec) -> str:
            return QCoreApplication.translate("Nugget", spec.title)

        def tr_description(spec) -> str:
            if not spec.description:
                return ""
            return QCoreApplication.translate("Nugget", spec.description)

        renderers = {
            Kind.SWITCH: lambda spec, target: make_switch(
                spec.id, tr_title(spec), tr_description(spec), target),
            Kind.TEXT: lambda spec, target: make_text_input(
                spec.id, tr_title(spec), tr_description(spec), target),
            Kind.NUMBER: lambda spec, target: make_number_input(
                spec.id, tr_title(spec), spec.min_value, spec.max_value,
                tr_description(spec), spec.step, target),
        }

        sections_to_render = self.sections if self.sections is not None else list(Section)
        hidden_sections = _hidden_sections()
        collapsed_sections = _load_collapsed_sections()
        for section in sections_to_render:
            if section in hidden_sections:
                continue
            collapsible = IOSCollapsibleSection(
                QCoreApplication.translate("Nugget", section.value),
                expanded=section.value not in collapsed_sections)
            collapsible.toggled.connect(
                lambda expanded, name=section.value: _save_collapsed_section(
                    name, not expanded))
            layout.addWidget(collapsible)
            start = len(self._search_rows)
            for spec in SPECS_BY_SECTION[section]:
                renderers[spec.kind](spec, collapsible.body_layout)
            section_rows = self._search_rows[start:]
            enabled_count = sum(
                bool(getattr(tweaks.get(row[1]), "enabled", False))
                for row in section_rows)
            collapsible.set_title_suffix(
                QCoreApplication.translate("Nugget", "  ·  {0}/{1} enabled")
                .format(enabled_count, len(section_rows)))
            self._search_sections.append((collapsible, section_rows))

        self.search_empty = IOSSearchEmpty(self)
        layout.addWidget(self.search_empty)
        layout.addStretch()

        # re-apply any remembered solarium-card visibility to the fresh card
        if self._solarium_visible is not None and self.force_solarium_fallback_card is not None:
            self.force_solarium_fallback_card.setVisible(self._solarium_visible)
        self._apply_search()
        pages = getattr(self.window, "ios_pages", None)
        if pages is not None and hasattr(self.window, "ios_nav"):
            if pages.currentWidget().isAncestorOf(self):
                QTimer.singleShot(0, lambda: self.window._update_shared_nav(
                    pages.currentIndex()))

    def _apply_search(self, *_args):
        searching = bool(self.search.text().strip())
        filter_mode = self.filter_control.currentData()
        filtering = searching or filter_mode != "all"
        favorites = self._favorites.names()
        matches = 0
        for card, tid, title, description, compatible in self._search_rows:
            enabled = bool(getattr(tweaks.get(tid), "enabled", False))
            available = compatible and not (
                tid == TweakID.ForceSolariumFallback and self._solarium_visible is False)
            if filter_mode == "enabled" and not enabled:
                available = False
            if filter_mode == "favorites" and tid.name not in favorites:
                available = False
            visible = available and self.search.matches(title, description, tid.name)
            card.setVisible(visible)
            matches += visible
        for section, rows in self._search_sections:
            section.setVisible(any(not row[0].isHidden() for row in rows))
            if filtering and section not in self._search_expanded:
                self._search_expanded[section] = section.expanded
            # Temporary expansion must not overwrite the user's saved collapse state.
            section.blockSignals(True)
            if filtering:
                section.set_expanded(True)
            elif section in self._search_expanded:
                section.set_expanded(self._search_expanded.pop(section))
            section.blockSignals(False)
            section.header.setEnabled(not filtering)
        self.search_empty.setVisible((searching or filter_mode != "all") and matches == 0)

    def refresh_section_counts(self):
        """Update enabled counts after a switch changes without rebuilding."""
        for section, rows in self._search_sections:
            enabled_count = sum(
                bool(getattr(tweaks.get(row[1]), "enabled", False))
                for row in rows)
            section.set_title_suffix(
                QCoreApplication.translate("Nugget", "  ·  {0}/{1} enabled")
                .format(enabled_count, len(rows)))

    def set_force_solarium_fallback_visible(self, visible: bool):
        # remember the intended state so a rebuild re-applies it (the card
        # pointer is recreated by rebuild())
        self._solarium_visible = visible
        self._apply_search()

    def _make_favorite_button(self, tweak_id, title):
        button = QPushButton(self)
        button.setFixedSize(44, 44)
        button.setCheckable(True)
        button.setChecked(tweak_id.name in self._favorites.names())
        self._set_favorite_icon(button, button.isChecked())
        button.setIconSize(QSize(23, 23))
        button.setCursor(Qt.PointingHandCursor)
        button.setAccessibleName(QCoreApplication.translate("Nugget", "Favorite: {0}").format(title))
        button.setToolTip(QCoreApplication.translate("Nugget", "Add or remove from favorites"))
        button.setStyleSheet(t("tweak_favorite_button"))
        button.toggled.connect(
            lambda selected, b=button, name=tweak_id.name:
            self._on_favorite_toggled(b, name, selected))
        self._favorite_buttons[tweak_id] = button
        return button

    def _refresh_favorites(self):
        names = self._favorites.names()
        for tid, button in self._favorite_buttons.items():
            selected = tid.name in names
            button.blockSignals(True)
            button.setChecked(selected)
            self._set_favorite_icon(button, selected)
            button.blockSignals(False)
        self._apply_search()

    def _on_favorite_toggled(self, button, name, selected):
        self._set_favorite_icon(button, selected)
        self._favorites.set_favorite(name, selected)

    def _set_favorite_icon(self, button, selected):
        colors = ColorThemeManager.instance().colors
        color = colors.accent if selected else colors.text_secondary
        icon = ":/icon/star-fill.svg" if selected else ":/icon/star.svg"
        button.setIcon(QIcon(theme_pixmap(
            icon, color, 23, button.devicePixelRatioF())))

    def _refresh_action_icons(self):
        for button in self._favorite_buttons.values():
            self._set_favorite_icon(button, button.isChecked())
        for button in self._info_buttons:
            button.setIcon(theme_icon(
                ":/icon/questionmark.circle.svg",
                ColorThemeManager.instance().colors.text_secondary))

    def _make_info_button(self, tweak_id, title):
        button = QPushButton(self)
        button.setFixedSize(36, 36)
        button.setIcon(theme_icon(":/icon/questionmark.circle.svg",
                                  ColorThemeManager.instance().colors.text_secondary))
        button.setIconSize(QSize(19, 19))
        button.setCursor(Qt.PointingHandCursor)
        help_text = QCoreApplication.translate("Nugget", "About {0}").format(title)
        button.setToolTip(help_text)
        button.setAccessibleName(help_text)
        button.setStyleSheet(t("tweak_info_button"))
        button.clicked.connect(lambda: self._show_tweak_info(tweak_id))
        self._info_buttons.append(button)
        return button

    def _show_tweak_info(self, tweak_id):
        from src.tweaks.registry import SPECS_BY_ID
        from src.gui.dialogs.tweak_info import TweakInfoDialog
        previous = getattr(self, '_tweak_info_dialog', None)
        if previous is not None:
            previous.close()
        dialog = TweakInfoDialog(SPECS_BY_ID[tweak_id], self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        self._tweak_info_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, '_tweak_info_dialog', None))
        dialog.show()

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self.filter_control._retheme()
        for lbl in self._switch_labels:
            lbl.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
        for button in self._info_buttons:
            button.setStyleSheet(t("tweak_info_button"))
        for button in self._favorite_buttons.values():
            button.setStyleSheet(t("tweak_favorite_button"))

    def _show_text_input_dialog(self, tweak_id: TweakID, title: str, current: str, row: IOSValueRow):
        saved = tweaks[tweak_id].value
        current = "" if saved is None else str(saved)
        dialog = TextInputDialog(title, current, self)
        if dialog.exec() == QDialog.Accepted:
            value = dialog.get_value()
            tweaks[tweak_id].set_value(value, toggle_enabled=True)
            display = value if value else QCoreApplication.translate("Nugget", "Empty")
            row.set_display_value(display)

    def _show_number_input_dialog(self, tweak_id: TweakID, title: str, current, row: IOSValueRow, min_val, max_val, step: float = 1.0):
        saved = tweaks[tweak_id].value
        current = 0 if saved is None else saved
        dialog = NumberInputDialog(title, current, min_val, max_val, self, step=step)
        if dialog.exec() == QDialog.Accepted:
            value = dialog.get_value()
            tweaks[tweak_id].set_value(value, toggle_enabled=True)
            row.set_display_value(_fmt_number(value))


class IOSTweaksPage(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("iosContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self._scroll = scroll
        self.content = IOSSectionContent(window, list(Section), self)
        scroll.setWidget(self.content)
        layout.addWidget(scroll)

        self._retheme()

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self._scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        self.content._retheme()

    def set_force_solarium_fallback_visible(self, visible: bool):
        self.content.set_force_solarium_fallback_visible(visible)

    def rebuild(self):
        self.content.rebuild()


class IOSSectionPage(QWidget):
    """Standalone iOS-style page for a single tweak section."""

    def __init__(self, window, section: Section, parent=None):
        super().__init__(parent)
        self.window = window
        self.section = section
        self.setObjectName("iosContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self._scroll = scroll
        self.content = IOSSectionContent(window, [section], self)
        scroll.setWidget(self.content)
        layout.addWidget(scroll)

        self._retheme()

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self._scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        self.content._retheme()

    def set_force_solarium_fallback_visible(self, visible: bool):
        self.content.set_force_solarium_fallback_visible(visible)

    def rebuild(self):
        self.content.rebuild()
