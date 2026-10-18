import sys
from PySide6.QtCore import (
    Qt, QCoreApplication, Slot, QTimer, QSize, QEvent, Signal, QThread,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QSizePolicy, QScrollArea, QProgressBar, QToolButton, QTabWidget
)

from src.gui.ios.components import IOSCard, IOSPrimaryButton
from src.gui.theme import t, ColorThemeManager, theme_icon, theme_pixmap

from src.gui.ios.feature_icons import FEATURE_ICONS
from src.devicemanagement.passcode_support import current_passcode_theme_reason


class _StorageThread(QThread):
    result = Signal(object, object, object)

    def __init__(self, udid, parent=None):
        super().__init__(parent)
        self.udid = udid

    def run(self):
        import asyncio
        try:
            total, free, battery = asyncio.run(self._query())
        except Exception:
            total, free, battery = None, None, None
        self.result.emit(total, free, battery)

    async def _query(self):
        from src.devicemanagement.session import lockdown_session
        from pymobiledevice3.services.diagnostics import DiagnosticsService
        async with lockdown_session(self.udid) as lockdown:
            battery = None
            try:
                async with DiagnosticsService(lockdown) as diagnostics:
                    try:
                        battery_report = await diagnostics.get_battery()
                        if isinstance(battery_report, dict):
                            percent = self._first_number(
                                battery_report, "CurrentCapacity", "BatteryCurrentCapacity")
                            if percent is not None:
                                charging = battery_report.get("IsCharging", False)
                                if isinstance(charging, str):
                                    charging = charging.casefold() in ("1", "true", "yes")
                                battery = {
                                    "percent": percent,
                                    "charging": bool(charging),
                                }
                    except Exception:
                        pass
                    report = await diagnostics.info("All")
                if isinstance(report, dict):
                    nested = report.get("DiskUsage") if isinstance(report.get("DiskUsage"), dict) else {}
                    total = report.get("TotalDataCapacity", nested.get("TotalDataCapacity"))
                    free = report.get("TotalDataSpace", nested.get("TotalDataSpace"))
                    if total is not None and free is not None:
                        return int(total), int(free), battery
            except Exception:
                # Some iOS versions reject the diagnostics relay request while
                # still exposing the same volume figures through AFC.
                pass

            from pymobiledevice3.services.afc import AfcService
            async with AfcService(lockdown) as afc:
                info = await afc.get_device_info()
            total = self._first_number(info, "FSTotalBytes", "TotalBytes")
            free = self._first_number(info, "FSFreeBytes", "FreeBytes")
            if total is None or free is None:
                return None, None, battery
            return total, free, battery

    @staticmethod
    def _first_number(values, *keys):
        if not isinstance(values, dict):
            return None
        for key in keys:
            value = values.get(key)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        return None


class _TileCard(IOSCard):
    """A home feature tile with a stationary hover outline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(False)

    def _retheme(self):
        self.setStyleSheet(t("home_tile"))


class _CardGrid(QWidget):
    """Keep visible home tiles in their final row, including before first show."""
    MIN_CARD_WIDTH = 140
    SPACING = 12
    MAX_COLUMNS = 6

    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self._cards = cards
        self._hidden = set()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(self.SPACING)
        self._grid.setVerticalSpacing(self.SPACING)
        for card in cards:
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            card.installEventFilter(self)
        self._layout_key = None
        self._reflow()

    def eventFilter(self, obj, event):
        if obj in self._cards:
            etype = event.type()
            if etype == QEvent.Hide:
                self._hidden.add(obj)
                self._reflow()
            elif etype == QEvent.Show:
                self._hidden.discard(obj)
                self._reflow()
        return super().eventFilter(obj, event)

    def reflow(self):
        self._reflow()

    def _reflow(self):
        include = [c for c in self._cards if c not in self._hidden]
        self.setMinimumWidth(
            len(include) * self.MIN_CARD_WIDTH + max(0, len(include) - 1) * self.SPACING)
        target = []
        if include:
            cols = min(len(include), self.MAX_COLUMNS)
            for i, card in enumerate(include):
                target.append((i // cols, i % cols, card))
        key = tuple((r, c, id(w)) for r, c, w in target)
        if key == self._layout_key:
            return
        for card in self._cards:
            self._grid.removeWidget(card)
        for col in range(self.MAX_COLUMNS):
            self._grid.setColumnStretch(col, 1 if col < len(include) else 0)
        for r, c, w in target:
            self._grid.addWidget(w, r, c)
        self._layout_key = key


class IOSHomePage(QWidget):
    # Feature tile: a big icon over the name. The tile height is left to the
    # layout so a subtitle that wraps to two lines grows the whole row.
    TILE_ICON_PX = 68

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("iosContainer")
        self._c = ColorThemeManager.instance().colors
        # (icon label, icon resource, title label, subtitle label) per tile
        self._tiles = []

        # Scroll area: the tile grid must never be squeezed below the tile
        # content height, so a short window scrolls instead of overlapping.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self._scroll = scroll
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Logo + Title row
        header = QHBoxLayout()
        header.setSpacing(8)

        # Load logo from resources
        self._logo = QLabel(self)
        self._logo.setFixedSize(88, 88)
        self._logo.setScaledContents(True)
        pixmap = QPixmap(":/credits/nugget_half_eaten.png")
        if not pixmap.isNull():
            self._logo.setPixmap(pixmap)
        else:
            self._logo.setStyleSheet(f"background-color: {self._c.bg_secondary}; border-radius: 14px;")
        header.addWidget(self._logo)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        title_layout.setAlignment(Qt.AlignVCenter)
        self._title = QLabel(QCoreApplication.translate("Nugget", "GoldenNugget"), self)
        self._title.setStyleSheet(t("home_title"))
        self._title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        title_layout.addWidget(self._title)

        self.subtitle = QLabel(QCoreApplication.translate("Nugget", "No device connected"), self)
        self.subtitle.setStyleSheet(t("home_subtitle"))
        self.subtitle.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.subtitle.setTextFormat(Qt.PlainText)
        title_layout.addWidget(self.subtitle)
        header.addLayout(title_layout)

        self.control_tabs = QTabWidget(self)
        self.control_tabs.setDocumentMode(True)
        self.control_tabs.setFixedHeight(116)
        self.control_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._developer_page = None
        if not getattr(sys, 'frozen', False):
            from src.gui.ios.developer import DeveloperPanel
            self._developer_page = DeveloperPanel(self.window, self.control_tabs)

        devices_page = QWidget(self.control_tabs)
        self._devices_page = devices_page
        devices_layout = QVBoxLayout(devices_page)
        devices_layout.setContentsMargins(12, 8, 12, 8)
        devices_layout.setSpacing(4)
        self.device_combo = QComboBox(devices_page)
        self.device_combo.setFixedHeight(36)
        devices_layout.addWidget(self.device_combo)
        self.status_lbl = QLabel("", devices_page)
        self.status_lbl.setTextFormat(Qt.RichText)
        self.status_lbl.setOpenExternalLinks(False)
        self.status_lbl.setWordWrap(False)
        self.status_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.status_lbl.linkActivated.connect(self._show_device_support)
        devices_layout.addWidget(self.status_lbl)
        self.control_tabs.addTab(devices_page, QCoreApplication.translate("Nugget", "Devices"))

        presets_page = QWidget(self.control_tabs)
        self._presets_page = presets_page
        presets_layout = QHBoxLayout(presets_page)
        presets_layout.setContentsMargins(10, 6, 10, 6)
        presets_layout.setSpacing(12)
        self.storage_card = IOSCard()
        self.storage_card.setFixedHeight(64)
        storage_layout = QVBoxLayout(self.storage_card)
        storage_layout.setContentsMargins(10, 7, 10, 7)
        storage_layout.setSpacing(3)
        self.storage_title = QLabel(QCoreApplication.translate("Nugget", "Device Storage"))
        self.storage_title.setStyleSheet(t("home_tile_title"))
        storage_layout.addWidget(self.storage_title)
        self.storage_bar = QProgressBar()
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(0)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setFixedHeight(6)
        storage_layout.addWidget(self.storage_bar)
        self.storage_lbl = QLabel(QCoreApplication.translate("Nugget", "Connect an iPhone to view storage"))
        self.storage_lbl.setStyleSheet(t("home_tile_subtitle"))
        self.storage_lbl.setWordWrap(False)
        storage_layout.addWidget(self.storage_lbl)
        self.presets_card = QWidget(presets_page)
        preset_content = QHBoxLayout(self.presets_card)
        preset_content.setContentsMargins(12, 4, 12, 4)
        preset_content.setSpacing(10)
        self.presets_icon = QLabel(self.presets_card)
        self.presets_icon.setPixmap(theme_pixmap(":/icon/folder.svg", self._c.accent, 26))
        self.presets_icon.setFixedSize(26, 26)
        preset_content.addWidget(self.presets_icon)
        preset_text = QVBoxLayout()
        preset_text.setContentsMargins(0, 0, 0, 0)
        preset_text.setSpacing(3)
        self.presets_title = QLabel(QCoreApplication.translate("Nugget", "PRESET"))
        self.presets_title.setStyleSheet(t("home_tile_title"))
        preset_text.addWidget(self.presets_title)
        self.presets_lbl = QLabel(QCoreApplication.translate("Nugget", "Manage presets"))
        self.presets_lbl.setStyleSheet(t("home_tile_subtitle"))
        self.presets_lbl.setWordWrap(False)
        preset_text.addWidget(self.presets_lbl)
        preset_content.addLayout(preset_text)
        self.manage_presets_btn = QPushButton(
            QCoreApplication.translate("Nugget", "Manage"), self.presets_card)
        self.manage_presets_btn.setFixedHeight(36)
        self.manage_presets_btn.setCursor(Qt.PointingHandCursor)
        self._style_manage_presets_button()
        self.manage_presets_btn.clicked.connect(self.open_presets_section)
        preset_content.addSpacing(6)
        preset_content.addWidget(self.manage_presets_btn)
        preset_content.addStretch(1)
        presets_layout.addWidget(self.presets_card, 1)
        self._storage_page = QWidget(self.control_tabs)
        storage_page_layout = QVBoxLayout(self._storage_page)
        storage_page_layout.setContentsMargins(10, 6, 10, 6)
        storage_page_layout.addWidget(self.storage_card)
        self._apply_home_widget()

        self._refresh_btn = QToolButton(self)
        self._refresh_btn.setFixedSize(92, 40)
        self._refresh_btn.setIconSize(QSize(21, 21))
        self._refresh_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._refresh_btn.setText(QCoreApplication.translate("Nugget", "Refresh"))
        self._style_utility_button(self._refresh_btn)
        self._refresh_btn.setToolTip(QCoreApplication.translate("Nugget", "Refresh connected devices"))
        self._apply_icon(self._refresh_btn, ":/icon/arrow-clockwise.svg")
        self._refresh_btn.clicked.connect(self.refresh_devices)
        self._logs_btn = QToolButton(self)
        self._logs_btn.setFixedSize(88, 40)
        self._logs_btn.setIconSize(QSize(21, 21))
        self._logs_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._logs_btn.setText(QCoreApplication.translate("Nugget", "App Log"))
        self._style_utility_button(self._logs_btn)
        self._logs_btn.setToolTip(QCoreApplication.translate("Nugget", "Open application log"))
        self._apply_icon(self._logs_btn, ":/icon/file-earmark-text.svg")
        self._logs_btn.clicked.connect(self.open_logs)
        self._settings_btn = QToolButton(self)
        self._settings_btn.setFixedSize(94, 40)
        self._settings_btn.setIconSize(QSize(21, 21))
        self._settings_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._settings_btn.setText(QCoreApplication.translate("Nugget", "Settings"))
        self._style_utility_button(self._settings_btn)
        self._settings_btn.setToolTip(QCoreApplication.translate("Nugget", "Settings"))
        self._apply_icon(self._settings_btn, ":/icon/gear.svg")
        self._settings_btn.clicked.connect(self.open_settings)
        utility_corner = QWidget(self.control_tabs)
        utility_layout = QHBoxLayout(utility_corner)
        utility_layout.setContentsMargins(0, 0, 4, 0)
        utility_layout.setSpacing(2)
        utility_layout.addWidget(self._refresh_btn)
        utility_layout.addWidget(self._logs_btn)
        utility_layout.addWidget(self._settings_btn)
        self.control_tabs.setCornerWidget(utility_corner, Qt.TopRightCorner)
        self._style_control_tabs()

        header.addWidget(self.control_tabs, 1)
        layout.addLayout(header)

        self._style_device_combo()
        self.populate_device_picker()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)

        self._storage_thread = None
        self.control_tabs.currentChanged.connect(self._on_control_tab_changed)

        cards_row = [self._make_card(
            "PosterBoard", "Animated wallpapers & templates", 2),
            self._make_card(
            "Tweaks", "Customize system settings", 1),
            self._make_card(
            "Daemons", "Disable system daemons", 3),
            self._make_card(
            "Status Bar", "Customize the status bar", 5),
            self._make_card(
            "Icon Themes", "Themed app icons & labels", 10),
            self._make_card(
            "Passcode Theme", "Custom keypad theme (.passthm)", 11)]
        (self.posterboard_card, self.tweaks_card,
         self.daemons_card, self.statusbar_card,
         self.icon_themes_card, self.passcode_theme_card) = cards_row
        self.cards_grid = _CardGrid(cards_row)
        layout.addWidget(self.cards_grid)

        # Apply / Reset share one row on the home screen.
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(12)

        apply_btn = IOSPrimaryButton(QCoreApplication.translate("Nugget", "Apply Tweaks"))
        apply_btn.clicked.connect(self.open_apply_classic)
        actions.addWidget(apply_btn, 1)

        layout.addLayout(actions)

        self.process_status_lbl = QLabel("", self)
        self.process_status_lbl.setWordWrap(True)
        self.process_status_lbl.setAlignment(Qt.AlignCenter)
        self.process_status_lbl.setStyleSheet(t("process_status_green"))
        self.process_status_lbl.hide()
        layout.addWidget(self.process_status_lbl)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_process_status)

        from src.gui.ios.operation_result import OperationResultCard
        self.result_card = OperationResultCard(self.open_logs, self.window.dismiss_operation_result)
        layout.addWidget(self.result_card)

        from src.gui.ios.support_panel import SupportPanel
        self.support_panel = SupportPanel(self)
        layout.addWidget(self.support_panel)
        layout.addStretch()

        # Paint the scroll area background for the active palette right away
        # (the shared _retheme only re-runs on a theme change).
        self._retheme()
        self.update_status()
        self.update_device_info()
        self.refresh_preset_widget()

    def _style_device_combo(self):
        c = self._c
        self.device_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c.bg_secondary};
                border: 1px solid {c.accent};
                border-radius: 18px;
                color: {c.text_primary};
                padding: 0 16px;
                font-size: 11.25pt;
            }}
            QComboBox::drop-down {{
                width: 30px;
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}
            QComboBox::down-arrow {{
                image: url(:/icon/caret-down-fill.svg);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.bg_secondary};
                color: {c.text_primary};
                selection-background-color: {c.accent};
            }}
        """)

    def _style_control_tabs(self):
        c = self._c
        self.control_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {c.bg_secondary};
                border: 1px solid {c.border};
                border-radius: 10px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {c.text_secondary};
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 5px 12px;
                margin: 3px 2px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {c.bg_tertiary};
                color: {c.text_primary};
                border-color: {c.border};
            }}
            QTabBar::tab:hover:!selected {{
                background: {c.surface_hover};
                color: {c.text_primary};
            }}
        """)

    def _style_utility_button(self, button):
        c = self._c
        button.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {c.text_secondary};
                border: 1px solid transparent;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {c.bg_secondary};
                color: {c.text_primary};
                border-color: {c.border};
            }}
            QToolButton:pressed {{ background: {c.surface_hover}; }}
        """)

    def _style_manage_presets_button(self):
        c = self._c
        self.manage_presets_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c.accent};
                color: {c.text_inverse};
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {c.accent_hover}; }}
            QPushButton:pressed {{ background: {c.accent}; }}
        """)

    def _apply_icon(self, button, resource_path: str):
        button.setIcon(theme_icon(resource_path, self._c.text_primary))

    def _retheme(self):
        self._c = ColorThemeManager.instance().colors
        c = self._c
        self._scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        if self._logo.pixmap() is None or self._logo.pixmap().isNull():
            self._logo.setStyleSheet(f"background-color: {c.bg_secondary}; border-radius: 14px;")
        self._title.setStyleSheet(t("home_title"))
        self.subtitle.setStyleSheet(t("home_subtitle"))
        self._style_control_tabs()
        self._style_device_combo()
        self._style_utility_button(self._refresh_btn)
        self._apply_icon(self._refresh_btn, ":/icon/arrow-clockwise.svg")
        self._style_utility_button(self._logs_btn)
        self._apply_icon(self._logs_btn, ":/icon/file-earmark-text.svg")
        self._style_utility_button(self._settings_btn)
        self._apply_icon(self._settings_btn, ":/icon/gear.svg")
        self.storage_title.setStyleSheet(t("home_tile_title"))
        self.storage_lbl.setStyleSheet(t("home_tile_subtitle"))
        self.storage_bar.setStyleSheet(f"""
            QProgressBar {{ background: {c.bg_input}; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {c.accent}; border-radius: 4px; }}
        """)
        self.presets_title.setStyleSheet(t("home_tile_title"))
        self.presets_lbl.setStyleSheet(t("home_tile_subtitle"))
        self.presets_icon.setPixmap(theme_pixmap(":/icon/folder.svg", c.accent, 26))
        self._style_manage_presets_button()
        self.process_status_lbl.setStyleSheet(t("process_status_green"))
        self.update_status()
        # Feature tiles: recolor the icon and restyle the two labels
        for icon_lbl, icon_res, title_lbl, sub_lbl in self._tiles:
            self._paint_tile_icon(icon_lbl, icon_res)
            title_lbl.setStyleSheet(t("home_tile_title"))
            sub_lbl.setStyleSheet(t("home_tile_subtitle"))
        self.update_passcode_support()

    def populate_device_picker(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        usb_devices = []
        try:
            devices = self.window.device_manager.devices
            usb_devices = [
                (index, device) for index, device in enumerate(devices)
                if device.connected_via_usb
            ]
            if usb_devices:
                for device_index, device in usb_devices:
                    self.device_combo.addItem(
                        theme_icon(":/icon/phone.svg", self._c.text_primary), device.name)
                    self.device_combo.setItemData(
                        self.device_combo.count() - 1, device_index, Qt.UserRole)
                selected = next(
                    (position for position, (device_index, _) in enumerate(usb_devices)
                     if device_index == self.window.device_manager.current_device_index),
                    0)
                self.device_combo.setCurrentIndex(selected)
            else:
                self.device_combo.addItem(QCoreApplication.translate("QCoreApplication", "No Device"))
        except Exception:
            self.device_combo.addItem(QCoreApplication.translate("QCoreApplication", "No Device"))
            usb_devices = []
        self.device_combo.blockSignals(False)
        self.device_combo.view().setMinimumWidth(max(
            self.device_combo.width(), self.device_combo.view().sizeHintForColumn(0) + 64))

    @Slot()
    def on_device_changed(self, index):
        if getattr(self, '_support_dialog', None) is not None:
            self._support_dialog.close()
        device_index = self.device_combo.itemData(index, Qt.UserRole)
        if device_index is not None:
            self.window.change_selected_device(device_index)
            self.update_device_info()
            self.update_status()

    @Slot()
    def refresh_devices(self):
        self.window.refresh_devices()

    @Slot()
    def open_settings(self):
        self.window.show_ios_page(4)

    @Slot()
    def open_logs(self):
        """Open the session-log viewer over the main window."""
        from src.gui.dialogs.log_viewer import LogViewerDialog
        dialog = LogViewerDialog(self.window)
        dialog.exec()

    def open_presets_section(self):
        self.window.open_presets_section()

    def switch_to_ios_page(self, index: int):
        self.window.show_ios_page(index)

    def open_apply_classic(self):
        """Open the dedicated Apply page before starting an operation."""
        self.window.show_ios_page(6)
        self.window._sync_sidebar_selection()

    def reset_tweaks(self):
        from src.gui.dialogs.reset_dialog import ResetDialog
        dialog = ResetDialog(device_manager=self.window.device_manager, apply_reset=self.window.apply_changes)
        dialog.exec()

    def show_process_status(self, text: str, success: bool = None):
        c = self._c
        if success is True:
            color = c.success
        elif success is False:
            color = c.error
        else:
            color = c.accent
        self.process_status_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {color}; background-color: transparent;")
        self.process_status_lbl.setText(text)
        self.process_status_lbl.show()
        self._hide_timer.stop()
        if success is not False and not getattr(self.window, "apply_in_progress", False):
            self._hide_timer.start(6000)

    def hide_process_status(self):
        self.process_status_lbl.hide()

    def update_status(self):
        c = self._c
        try:
            if self.window.device_manager.get_current_device_udid():
                if not self.window.device_manager.get_current_device_is_supported_by_fork():
                    status_text = QCoreApplication.translate(
                        "QCoreApplication", "Not Supported.")
                    color = c.error
                elif self.window.device_manager.get_current_device_partially_supported():
                    status_text = QCoreApplication.translate("Nugget", "Partially Supported")
                    color = c.warning
                else:
                    status_text = QCoreApplication.translate("QCoreApplication", "Supported!")
                    color = c.success
            else:
                status_text = QCoreApplication.translate("Nugget", "Not connected")
                color = c.text_primary
        except AttributeError:
            status_text = QCoreApplication.translate("Nugget", "Not connected")
            color = c.text_primary
        if self.window.device_manager.get_current_device_udid():
            self.status_lbl.setText(
                f"<a href='support' style='color:{color}; text-decoration:none;'>"
                f"{status_text}  ⓘ</a>")
            self.status_lbl.setToolTip(QCoreApplication.translate(
                "Nugget", "View device compatibility and safety restrictions."))
        else:
            self.status_lbl.setText(f"<span style='color:{color};'>{status_text}</span>")
            self.status_lbl.setToolTip("")
        self.status_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; padding-left: 2px; color: {color};")

    def _show_device_support(self, _link=None):
        if not self.window.device_manager.get_current_device_udid():
            return
        from src.gui.dialogs.device_support import DeviceSupportDialog
        previous = getattr(self, '_support_dialog', None)
        if previous is not None:
            previous.raise_()
            previous.activateWindow()
            return
        dialog = DeviceSupportDialog(self.window.device_manager, self.window)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        self._support_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, '_support_dialog', None))
        dialog.show()

    def update_device_info(self):
        if getattr(self, '_support_dialog', None) is not None:
            self._support_dialog.close()
        try:
            ver = self.window.device_manager.get_current_device_version()
            build = self.window.device_manager.get_current_device_build()
            if ver:
                text = QCoreApplication.translate("Nugget", "iOS {0}").format(ver)
                if build:
                    text += "  ·  " + QCoreApplication.translate("Nugget", "Build {0}").format(build)
                self.subtitle.setText(text)
            else:
                self.subtitle.setText(QCoreApplication.translate("Nugget", "No device connected"))
        except AttributeError:
            self.subtitle.setText(QCoreApplication.translate("Nugget", "No device connected"))
        self.update_passcode_support()
        self._refresh_storage()

    def update_passcode_support(self):
        reason = current_passcode_theme_reason(self.window.device_manager)
        self.passcode_theme_card.setEnabled(not reason)
        icon, resource, title, caption = self._tiles[-1]
        if reason:
            message = "Your version is not supported" if self.window.device_manager.get_current_device_udid() else "Connect an iPhone"
            caption.setText(QCoreApplication.translate("Nugget", message))
        else:
            caption.setText(QCoreApplication.translate("Nugget", "Custom keypad theme (.passthm)"))
        self.passcode_theme_card.setAccessibleDescription(reason or "")
        color = self._c.text_disabled if reason else self._c.text_secondary
        caption.setStyleSheet(t("home_tile_subtitle") + f"color: {color};")
        title.setStyleSheet(t("home_tile_title") +
                           f"color: {self._c.text_disabled if reason else self._c.text_primary};")
        icon.setPixmap(theme_pixmap(resource,
            self._c.text_disabled if reason else self._c.text_primary,
            self.TILE_ICON_PX, self.devicePixelRatioF()))

    def _refresh_storage(self):
        # Also feeds the pre-apply warnings in MainWindow, so always collect
        # the figures even while the storage card is not the active widget.
        if self._storage_thread is not None and self._storage_thread.isRunning():
            return
        udid = self.window.device_manager.get_current_device_udid()
        if not udid:
            self.window._storage_info = None
            self.window._battery_info = None
            self.storage_bar.setValue(0)
            self.storage_lbl.setText(QCoreApplication.translate(
                "Nugget", "Connect an iPhone to view storage"))
            return
        self.storage_lbl.setText(QCoreApplication.translate("Nugget", "Loading storage…"))
        self._storage_thread = _StorageThread(udid, self)
        self._storage_thread.result.connect(self._on_storage_result)
        self._storage_thread.start()

    @Slot(object, object)
    def _on_storage_result(self, total, free, battery):
        current_udid = self.window.device_manager.get_current_device_udid()
        sender = self.sender()
        if sender is not self._storage_thread or getattr(sender, "udid", None) != current_udid:
            QTimer.singleShot(0, self._refresh_storage)
            return
        if not total or free is None or total <= 0:
            self.window._storage_info = None
            self.window._battery_info = None
            self.storage_bar.setValue(0)
            self.storage_lbl.setText(QCoreApplication.translate(
                "Nugget", "Storage information unavailable"))
            return
        self.window._storage_info = {
            "udid": current_udid, "total": int(total), "free": int(free)
        }
        self.window._battery_info = {
            "udid": current_udid, **(battery or {})
        } if battery is not None else None
        used = max(0, total - free)
        percent = min(100, round(used * 100 / total))
        self.storage_bar.setValue(percent)
        self.storage_lbl.setText(QCoreApplication.translate(
            "Nugget", "Used {0} GB · Free {1} GB").format(
                self._format_gb(used), self._format_gb(free)))

    @staticmethod
    def _format_gb(value):
        return f"{value / (1024 ** 3):.1f}"

    def refresh_device_combo(self):
        self.populate_device_picker()

    def _home_widget_mode(self) -> str:
        try:
            mode = self.window.settings.value("home_widget", "presets", type=str)
        except Exception:
            mode = "presets"
        return mode if mode in ("storage", "presets", "both") else "presets"

    def _apply_home_widget(self):
        mode = self._home_widget_mode()
        current = self.control_tabs.currentWidget()
        self._presets_page.hide()
        self._storage_page.hide()
        self.control_tabs.blockSignals(True)
        while self.control_tabs.count():
            self.control_tabs.removeTab(0)
        if self._developer_page is not None:
            self.control_tabs.addTab(self._developer_page, QCoreApplication.translate("Nugget", "Developer"))
        self.control_tabs.addTab(self._devices_page, QCoreApplication.translate("Nugget", "Devices"))
        if mode in ("presets", "both"):
            self.control_tabs.addTab(self._presets_page, QCoreApplication.translate("Nugget", "Presets"))
        if mode in ("storage", "both"):
            self.control_tabs.addTab(self._storage_page, QCoreApplication.translate("Nugget", "Device Storage"))
        if current is not None and self.control_tabs.indexOf(current) >= 0:
            self.control_tabs.setCurrentWidget(current)
        # A preferred width, not a fixed one: the window is only 1000px wide,
        # so the panel must give way to the logo + title instead of pushing
        # the whole page into a horizontal scroll.
        width = 640 if mode == "both" else 560
        self.control_tabs.setMaximumWidth(width + (100 if self._developer_page is not None else 0))
        self.control_tabs.blockSignals(False)

    def _on_control_tab_changed(self, index):
        if self.control_tabs.widget(index) is self._storage_page:
            self._refresh_storage()

    def set_home_widget(self, mode: str):
        if mode not in ("storage", "presets", "both"):
            return
        self.window.settings.setValue("home_widget", mode)
        self.window._sync_settings()
        self._apply_home_widget()
        selected = self._storage_page if mode == "storage" else self._presets_page
        self.control_tabs.setCurrentWidget(selected)
        if mode in ("presets", "both"):
            self.refresh_preset_widget()
        if mode in ("storage", "both"):
            self._refresh_storage()

    def refresh_preset_widget(self):
        """Keep the top-bar preset card's subtitle in sync."""
        try:
            autosave = self.window.autosave_enabled()
        except Exception:
            autosave = True
        name = self.window.settings.value("last_loaded_preset", "", type=str) or ""
        if name:
            self.presets_lbl.setText(name)
        elif autosave:
            self.presets_lbl.setText(QCoreApplication.translate("Nugget", "AutoSave"))
        else:
            self.presets_lbl.setText(QCoreApplication.translate("Nugget", "Manage presets"))

    def set_statusbar_visible(self, visible: bool):
        self.statusbar_card.setVisible(visible)
        self.cards_grid.reflow()

    def _make_card(self, title: str, subtitle: str, page_index: int) -> IOSCard:
        """One home feature tile: a big themed icon with the name below it."""
        card = _TileCard()
        card.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Preferred)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 20, 10, 16)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignHCenter)

        icon_res = FEATURE_ICONS.get(title, ":/icon/compass.svg")
        icon_lbl = QLabel(card)
        icon_lbl.setFixedSize(self.TILE_ICON_PX, self.TILE_ICON_PX)
        icon_lbl.setAlignment(Qt.AlignCenter)
        # transparent, so the label never paints the palette window color over
        # the tile (see the home_tile_* styles)
        icon_lbl.setStyleSheet("background-color: transparent;")
        self._paint_tile_icon(icon_lbl, icon_res)
        card_layout.addWidget(icon_lbl, 0, Qt.AlignHCenter)

        title_lbl = QLabel(QCoreApplication.translate("Nugget", title), card)
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(t("home_tile_title"))
        card_layout.addWidget(title_lbl, 0, Qt.AlignHCenter)

        sub_lbl = QLabel(QCoreApplication.translate("Nugget", subtitle), card)
        sub_lbl.setWordWrap(True)
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet(t("home_tile_subtitle"))
        card_layout.addWidget(sub_lbl, 0, Qt.AlignHCenter)

        card_layout.addStretch(1)

        # kept for _retheme(): icons are recolored, labels restyled
        self._tiles.append((icon_lbl, icon_res, title_lbl, sub_lbl))

        card.mousePressEvent = lambda e: self.switch_to_ios_page(page_index)
        card.setCursor(Qt.PointingHandCursor)
        return card

    def _paint_tile_icon(self, label: QLabel, icon_res: str):
        """Draw a feature icon at tile size (and screen density) in the
        current text color."""
        label.setPixmap(theme_pixmap(
            icon_res, self._c.text_primary, self.TILE_ICON_PX,
            self.devicePixelRatioF()))
