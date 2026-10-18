from PySide6.QtCore import Qt, QCoreApplication, QTimer, QSize
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QLabel,
    QDialog, QPushButton
)
from packaging.version import Version, InvalidVersion

from src.gui.ios.components import (
    IOSCard, IOSSectionHeader, IOSSwitch,
    TextInputDialog, NumberInputDialog
)
from src.gui.theme import ColorThemeManager, theme_icon, t
from src.gui.ios.statusbar_preview import StatusBarPreview, preview_state
from src.tweaks.tweaks import tweaks, TweakID
from src.tweaks.status_bar.status_setter import StatusBarItem

# iOS 27 dropped the classic statusBarOverrides struct: only the cellular
# entry survives, through StatusBarOverrides.archive, and that entry carries
# the carrier name, its service badge and its signal-bar count. Everything
# else (time, date, battery, wifi, and the per-item show/hide toggles) has no
# representation there, so it is hidden rather than shown as a switch that
# silently does nothing. See src/tweaks/status_bar/statusbar_archive.py.
FIRST_ARCHIVE_VERSION = "27.0"


class IOSStatusBarPage(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("iosContainer")
        self.status_manager = tweaks[TweakID.StatusBar]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll = scroll
        content = QWidget()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(16, 16, 16, 32)
        self.content_layout.setSpacing(10)

        # (widget, survives iOS 27) for every card and section header, so the
        # whole page can be re-gated whenever the connected device changes.
        self._rows: list[tuple[QWidget, bool]] = []

        # Live preview of what the device will show; refreshed after every edit.
        self.preview = StatusBarPreview()
        self.content_layout.addWidget(self.preview)

        # Master enable switch
        self._header(QCoreApplication.translate("Nugget", "Configuration"), survives_ios27=True)
        self.enabled_switch = self._make_switch(
            QCoreApplication.translate("Nugget", "Enable Status Bar Modifications"),
            self.status_manager.enabled,
            self._on_enabled_toggled,
            survives_ios27=True,
        )

        # Text rows
        self._header(QCoreApplication.translate("Nugget", "Text Overrides"), survives_ios27=True)
        self.time_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Status Bar Time Text*"),
            self.status_manager.is_time_overridden(),
            self.status_manager.get_time_override(),
            self.status_manager.set_time, self.status_manager.unset_time,
        )
        self.date_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Status Bar Date Text"),
            self.status_manager.is_date_overridden(),
            self.status_manager.get_date_override(),
            self.status_manager.set_date, self.status_manager.unset_date,
        )
        self.breadcrumb_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Breadcrumb Text"),
            self.status_manager.is_crumb_overridden(),
            self.status_manager.get_crumb_override(),
            self.status_manager.set_crumb, self.status_manager.unset_crumb,
        )
        self.battery_detail_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Battery Detail Text"),
            self.status_manager.is_battery_detail_overridden(),
            self.status_manager.get_battery_detail_override(),
            self.status_manager.set_battery_detail, self.status_manager.unset_battery_detail,
        )
        self.carrier_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Carrier Text"),
            self.status_manager.is_carrier_overridden(),
            self.status_manager.get_carrier_override(),
            self.status_manager.set_carrier_override, self.status_manager.unset_carrier_override,
            survives_ios27=True,
        )
        self.badge_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Change Service Badge Text"),
            self.status_manager.is_primary_service_badge_overridden(),
            self.status_manager.get_primary_service_badge_override(),
            self.status_manager.set_primary_service_badge, self.status_manager.unset_primary_service_badge,
            survives_ios27=True,
        )
        self.secondary_carrier_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Secondary Carrier Name"),
            self.status_manager.is_secondary_carrier_overridden(),
            self.status_manager.get_secondary_carrier_override(),
            self.status_manager.set_secondary_carrier_override, self.status_manager.unset_secondary_carrier_override,
            survives_ios27=True,
        )
        self.secondary_badge_row = self._make_text_row(
            QCoreApplication.translate("Nugget", "Secondary Service Badge"),
            self.status_manager.is_secondary_service_badge_overridden(),
            self.status_manager.get_secondary_service_badge_override(),
            self.status_manager.set_secondary_service_badge, self.status_manager.unset_secondary_service_badge,
            survives_ios27=True,
        )

        # Number rows
        self._header(QCoreApplication.translate("Nugget", "Signal & Battery Levels"))
        self.gsm_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Change Signal Strength"),
            self.status_manager.is_gsm_signal_strength_bars_overridden(),
            self.status_manager.get_gsm_signal_strength_bars_override(),
            self.status_manager.set_gsm_signal_strength_bars, self.status_manager.unset_gsm_signal_strength_bars,
            0, 5,
            survives_ios27=True,
        )
        self.secondary_gsm_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Secondary Cellular Signal Bars"),
            self.status_manager.is_secondary_gsm_signal_strength_bars_overridden(),
            self.status_manager.get_secondary_gsm_signal_strength_bars_override(),
            self.status_manager.set_secondary_gsm_signal_strength_bars, self.status_manager.unset_secondary_gsm_signal_strength_bars,
            0, 5,
            survives_ios27=True,
        )
        self.wifi_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Change Wi-Fi Signal Strength"),
            self.status_manager.is_wifi_signal_strength_bars_overridden(),
            self.status_manager.get_wifi_signal_strength_bars_override(),
            self.status_manager.set_wifi_signal_strength_bars, self.status_manager.unset_wifi_signal_strength_bars,
            0, 5,
        )
        self.battery_capacity_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Change Battery Icon Capacity"),
            self.status_manager.is_battery_capacity_overridden(),
            self.status_manager.get_battery_capacity_override(),
            self.status_manager.set_battery_capacity, self.status_manager.unset_battery_capacity,
            0, 100,
        )
        self.network_type_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Change Data Network Type"),
            self.status_manager.is_data_network_type_overridden(),
            self.status_manager.get_data_network_type_override(),
            self.status_manager.set_data_network_type, self.status_manager.unset_data_network_type,
            0, 30,
        )
        self.secondary_network_type_row = self._make_number_row(
            QCoreApplication.translate("Nugget", "Secondary Data Network Type"),
            self.status_manager.is_secondary_data_network_type_overridden(),
            self.status_manager.get_secondary_data_network_type_override(),
            self.status_manager.set_secondary_data_network_type, self.status_manager.unset_secondary_data_network_type,
            0, 30,
        )

        # Raw signal strength
        self._header(QCoreApplication.translate("Nugget", "Signal Measurements"))
        self._make_switch(
            QCoreApplication.translate("Nugget", "Show Numeric Cellular Strength"),
            self.status_manager.is_raw_gsm_signal_shown(),
            lambda checked: self.status_manager.show_raw_gsm_signal(checked),
        )
        self._make_switch(
            QCoreApplication.translate("Nugget", "Show Numeric Wi-Fi Strength"),
            self.status_manager.is_raw_wifi_signal_shown(),
            lambda checked: self.status_manager.show_raw_wifi_signal(checked),
        )

        # Item show/hide toggles
        self._header(QCoreApplication.translate("Nugget", "Icon Visibility"))
        for name, item in [
            (QCoreApplication.translate("Nugget", "Disable Focus Mode icon"), StatusBarItem.QuietModeStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Airplane Mode icon"), StatusBarItem.AirplaneModeStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Cellular Service icon"), StatusBarItem.CellularServiceStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Wi-Fi icon"), StatusBarItem.CellularDataNetworkStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Battery icon"), StatusBarItem.MainBatteryStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Bluetooth icon"), StatusBarItem.BluetoothStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Alarm icon"), StatusBarItem.AlarmStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Location icon"), StatusBarItem.LocationStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Rotation Lock icon"), StatusBarItem.RotationLockStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable AirPlay icon"), StatusBarItem.AirPlayStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable CarPlay icon"), StatusBarItem.CarPlayStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable VPN icon"), StatusBarItem.VPNStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Voice Control icon"), StatusBarItem.VoiceControlStatusBarItem),
            (QCoreApplication.translate("Nugget", "Disable Liquid Detection Warning icon"), StatusBarItem.LiquidDetectionStatusBarItem),
        ]:
            overridden = self.status_manager.is_item_overridden(item)
            hidden = overridden and self.status_manager.get_item_override(item) == 0
            self._make_switch(
                name,
                hidden,
                self._make_item_handler(item),
            )

        # Silly mode
        self._header(QCoreApplication.translate("Nugget", "Additional Options"))
        self._make_switch(
            QCoreApplication.translate("Nugget", "Silly Mode"),
            self.status_manager.is_silly_mode_enabled(),
            lambda checked: self.status_manager.toggle_silly_mode(checked),
        )

        # Explains the trimmed page on iOS 27; hidden everywhere else.
        self._ios27_note = QLabel(QCoreApplication.translate(
            "Nugget",
            "iOS 27 replaced the status bar override file, so only the carrier "
            "entry can be changed here: its name, service badge and signal bars. "
            "The badge and bars apply to the carrier name, so set one first. "
            "The carrier entry is replaced as a whole, so the network-type "
            "indicator is never overridden and the signal bars stay at the "
            "value you set (empty by default) rather than following the real "
            "signal. The other options need iOS 26 or lower."
        ))
        self._ios27_note.setWordWrap(True)
        self.content_layout.addWidget(self._ios27_note)

        self.content_layout.addStretch()

        self._retheme()
        self._sync_controls_enabled()
        # Every control on this page is an IOSSwitch or an edit dialog; the
        # switches' own handlers update the tweak first, the preview follows.
        for switch in self.findChildren(IOSSwitch):
            switch.toggled.connect(self._schedule_preview_refresh)
        self._refresh_preview()

    def showEvent(self, event):
        super().showEvent(event)
        # The page outlives device changes, so re-gate every time it is shown.
        self._apply_ios27_gating()
        self._sync_controls_enabled()
        self._refresh_preview()

    def _schedule_preview_refresh(self, *_):
        QTimer.singleShot(0, self._refresh_preview)

    def _refresh_preview(self):
        self.preview.set_state(preview_state(self.status_manager, self._is_ios27()))

    def _current_version(self) -> str:
        try:
            return self.window.device_manager.get_current_device_version() or ""
        except Exception:
            return ""

    def _is_ios27(self) -> bool:
        version = self._current_version()
        if not version:
            return False
        try:
            return Version(version) >= Version(FIRST_ARCHIVE_VERSION)
        except InvalidVersion:
            return False

    def _apply_ios27_gating(self):
        is_ios27 = self._is_ios27()
        for widget, survives in self._rows:
            widget.setVisible(not is_ios27 or survives)
        self._ios27_note.setVisible(is_ios27)
        pages = getattr(self.window, "ios_pages", None)
        if pages is not None and hasattr(self.window, "ios_nav"):
            if pages.currentWidget() is self:
                QTimer.singleShot(0, lambda: self.window._update_shared_nav(
                    pages.currentIndex()))

    def _header(self, title: str, survives_ios27: bool = False):
        header = IOSSectionHeader(title)
        tr = lambda text: QCoreApplication.translate("Nugget", text)
        names = {
            tr("Text Overrides"): tr("Text"),
            tr("Signal & Battery Levels"): tr("Signal Levels"),
            tr("Signal Measurements"): tr("Measurements"),
            tr("Icon Visibility"): tr("Visibility"),
            tr("Additional Options"): tr("Options"),
        }
        header.setProperty("navigationTitle", names.get(title, title))
        self.content_layout.addWidget(header)
        self._rows.append((header, survives_ios27))
        return header

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self._scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        if hasattr(self, "preview"):
            self.preview.update()  # its captions use the theme's muted text colour
        # Transparent background so it does not read as a dark box, muted text
        # because it is a note rather than a value.
        self._ios27_note.setStyleSheet(
            f"background-color: transparent; color: {c.text_secondary}; font-size: 14px;")
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue
            # Style labels inside cards (switch rows, text rows, number rows)
            row = widget.findChild(QHBoxLayout)
            if row is not None:
                for j in range(row.count()):
                    child = row.itemAt(j)
                    if child is None:
                        continue
                    w = child.widget()
                    if w is None:
                        continue
                    if isinstance(w, QLabel):
                        current = w.styleSheet()
                        if "font-size: 15px" in current:
                            w.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
                        elif "font-size: 14px" in current:
                            w.setStyleSheet(f"color: {c.text_secondary}; font-size: 14px; background-color: transparent;")
                        elif "font-size: 17px" in current:
                            w.setStyleSheet(f"color: {c.accent}; font-size: 17px; background-color: transparent;")
            for button in widget.findChildren(QPushButton):
                if button.objectName() == "statusBarEdit":
                    button.setStyleSheet(t("tweak_info_button"))
                    button.setIcon(theme_icon(":/icon/edit-value.svg", c.text_secondary))

    def _sync_controls_enabled(self):
        self.enabled_switch.blockSignals(True)
        self.enabled_switch.setChecked(self.status_manager.enabled)
        self.enabled_switch.blockSignals(False)
        master_card = self.enabled_switch.parentWidget()
        for card, _ in self._rows:
            if isinstance(card, IOSCard):
                card.setEnabled(card is master_card or self.status_manager.enabled)

    def _make_edit_button(self, callback):
        button = QPushButton(self)
        button.setObjectName("statusBarEdit")
        button.setFixedSize(44, 36)
        button.setIconSize(QSize(19, 19))
        button.setIcon(theme_icon(":/icon/edit-value.svg", ColorThemeManager.instance().colors.text_secondary))
        button.setToolTip(QCoreApplication.translate("Nugget", "Edit value"))
        button.setAccessibleName(button.toolTip())
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(t("tweak_info_button"))
        button.clicked.connect(callback)
        return button

    def _make_item_handler(self, item: StatusBarItem):
        def handler(checked: bool):
            if checked:
                # switch ON → the icon is disabled (forced hidden)
                self.status_manager.set_item_override(item, False)
            elif self.status_manager.is_item_overridden(item):
                # switch OFF → back to the stock default visibility
                self.status_manager.unset_item_override(item)
        return handler

    def _make_switch(self, title: str, checked: bool, on_toggled, survives_ios27: bool = False):
        c = ColorThemeManager.instance().colors
        card = IOSCard()
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        label = QLabel(title)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
        row.addWidget(label, 1)
        switch = IOSSwitch(checked)
        switch.toggled.connect(on_toggled)
        row.addWidget(switch)
        row.addSpacing(56)
        self.content_layout.addWidget(card)
        self._rows.append((card, survives_ios27))
        return switch
    def _make_text_row(self, title: str, overridden: bool, current: str, setter, unsetter, survives_ios27: bool = False):
        c = ColorThemeManager.instance().colors
        card = IOSCard()
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        label = QLabel(title)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
        row.addWidget(label, 1)

        card.setProperty("overrideValue", current)
        value_lbl = QLabel(current if overridden else QCoreApplication.translate("Nugget", "Default"))
        value_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 14px; background-color: transparent;")
        value_lbl.setMaximumWidth(180)
        value_lbl.setWordWrap(True)
        self._fit_default_value(value_lbl)
        row.addWidget(value_lbl)

        switch = IOSSwitch(overridden)
        switch.toggled.connect(lambda checked: self._on_text_row_toggled(checked, setter, unsetter, label, value_lbl, card.property("overrideValue")))
        row.addWidget(switch)

        edit_btn = self._make_edit_button(lambda: self._on_text_row_edit(
            title, card.property("overrideValue"), setter, label, value_lbl))
        row.addWidget(edit_btn)

        self.content_layout.addWidget(card)
        self._rows.append((card, survives_ios27))
        return switch
    @staticmethod
    def _fit_default_value(value_lbl: QLabel):
        """Keep "Default" on one line: a word-wrapped label next to a
        stretching title is squeezed to its narrowest word, so a two-word
        translation ("По умолчанию") broke onto two lines."""
        font = QFont(value_lbl.font())
        font.setPixelSize(14)  # matches the label's stylesheet font-size
        width = QFontMetrics(font).horizontalAdvance(
            QCoreApplication.translate("Nugget", "Default"))
        value_lbl.setMinimumWidth(min(180, width + 2))

    def _on_text_row_toggled(self, checked: bool, setter, unsetter, label, value_lbl, current: str):
        if checked:
            setter(current)
        else:
            unsetter()
        value_lbl.setText(current if checked else QCoreApplication.translate("Nugget", "Default"))

    def _on_text_row_edit(self, title: str, current: str, setter, label, value_lbl):
        dialog = TextInputDialog(title, current, self)
        if dialog.exec() == QDialog.Accepted:
            value = dialog.get_value()
            setter(value)
            card = value_lbl.parentWidget()
            card.setProperty("overrideValue", value)
            switch = card.findChild(IOSSwitch)
            switch.blockSignals(True)
            switch.setChecked(True)
            switch.blockSignals(False)
            value_lbl.setText(value if value else QCoreApplication.translate("Nugget", "Default"))
            label.setText(title)
            self._refresh_preview()

    def _make_number_row(self, title: str, overridden: bool, current: int, setter, unsetter, min_val: int, max_val: int, survives_ios27: bool = False):
        c = ColorThemeManager.instance().colors
        card = IOSCard()
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        label = QLabel(title)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; background-color: transparent;")
        row.addWidget(label, 1)

        card.setProperty("overrideValue", current)
        value_lbl = QLabel(str(current) if overridden else QCoreApplication.translate("Nugget", "Default"))
        value_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 14px; background-color: transparent;")
        value_lbl.setMaximumWidth(180)
        value_lbl.setWordWrap(True)
        self._fit_default_value(value_lbl)
        row.addWidget(value_lbl)

        switch = IOSSwitch(overridden)
        switch.toggled.connect(lambda checked: self._on_number_row_toggled(checked, setter, unsetter, value_lbl, card.property("overrideValue")))
        row.addWidget(switch)

        edit_btn = self._make_edit_button(lambda: self._on_number_row_edit(
            title, card.property("overrideValue"), setter, value_lbl, min_val, max_val))
        row.addWidget(edit_btn)

        self.content_layout.addWidget(card)
        self._rows.append((card, survives_ios27))
        return switch
    def _on_number_row_toggled(self, checked: bool, setter, unsetter, value_lbl, current: int):
        if checked:
            setter(current)
        else:
            unsetter()
        value_lbl.setText(str(current) if checked else QCoreApplication.translate("Nugget", "Default"))

    def _on_number_row_edit(self, title: str, current: int, setter, value_lbl, min_val: int, max_val: int):
        dialog = NumberInputDialog(title, current, min_val, max_val, self)
        if dialog.exec() == QDialog.Accepted:
            value = dialog.get_value()
            setter(value)
            card = value_lbl.parentWidget()
            card.setProperty("overrideValue", value)
            switch = card.findChild(IOSSwitch)
            switch.blockSignals(True)
            switch.setChecked(True)
            switch.blockSignals(False)
            value_lbl.setText(str(value))
            self._refresh_preview()

    def _on_enabled_toggled(self, checked: bool):
        self.status_manager.set_enabled(checked)
        self._sync_controls_enabled()
