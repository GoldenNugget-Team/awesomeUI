from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QHBoxLayout

from src.gui.ios.components import IOSPrimaryButton
from src.gui.theme import t, theme_pixmap, ColorThemeManager


class ConnectDevicePlaceholder(QWidget):
    """Full-screen placeholder shown while no supported iPhone is connected.

    Occupies the iOS content stack on its own (outside the nav-bar root), so
    it renders edge-to-edge with no back button. Self-connects to the color
    theme signal and repaints via :meth:`_retheme`.
    """

    ICON_PX = 120

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("iosContainer")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        content = QWidget()
        self._scroll.setWidget(content)
        root.addWidget(self._scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignCenter)

        self._icon_lbl = QLabel(self)
        self._icon_lbl.setFixedSize(self.ICON_PX, self.ICON_PX)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._icon_lbl, 0, Qt.AlignHCenter)

        self._title = QLabel(
            QCoreApplication.translate("Nugget", "No device connected"), self)
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)

        self._message = QLabel(
            QCoreApplication.translate(
                "Nugget", "Connect an Apple device with iOS 26.2+"), self)
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        self._steps = QLabel(QCoreApplication.translate("Nugget",
            "1. Connect your iPhone or iPad using a data cable.\n"
            "2. Unlock it and keep the screen awake.\n"
            "3. Tap Trust on the device if prompted, then check again."))
        self._steps.setWordWrap(True)
        self._steps.setFixedWidth(650)
        self._steps.setTextFormat(Qt.PlainText)
        layout.addWidget(self._steps, 0, Qt.AlignHCenter)

        self._refresh_btn = IOSPrimaryButton(
            QCoreApplication.translate("Nugget", "Check connection"), self)
        self._refresh_btn.setMinimumWidth(240)
        self._refresh_btn.clicked.connect(self._refresh)
        layout.addWidget(self._refresh_btn, 0, Qt.AlignHCenter)

        actions = QHBoxLayout()
        actions.addStretch()
        self._diagnostics_btn = QPushButton(QCoreApplication.translate("Nugget", "Connection help"))
        self._diagnostics_btn.setCheckable(True)
        self._diagnostics_btn.toggled.connect(lambda shown: self._help_detail.setVisible(shown))
        self._logs_btn = QPushButton(QCoreApplication.translate("Nugget", "Open application log"))
        self._logs_btn.clicked.connect(lambda: self.window.ios_home.open_logs())
        actions.addWidget(self._diagnostics_btn)
        actions.addWidget(self._logs_btn)
        actions.addStretch()
        layout.addLayout(actions)
        import sys
        platform_hint = QCoreApplication.translate("Nugget",
            "Linux: install usbmuxd and libimobiledevice and make sure usbmuxd is running.") if sys.platform.startswith('linux') else QCoreApplication.translate("Nugget",
            "Windows: install Apple Devices or Apple's iTunes and reconnect the device.") if sys.platform == 'win32' else QCoreApplication.translate("Nugget",
            "macOS: check whether the device appears in Finder and confirm Trust.")
        self._help_detail = QLabel(platform_hint + "\n" + QCoreApplication.translate("Nugget",
            "Try another data cable or USB port. Charging alone does not confirm a data connection. Open the log for the exact scan error."))
        self._help_detail.setFixedWidth(650)
        self._help_detail.setWordWrap(True)
        self._help_detail.setTextFormat(Qt.PlainText)
        self._help_detail.hide()
        layout.addWidget(self._help_detail, 0, Qt.AlignHCenter)
        self._scan_status = QLabel()
        self._scan_status.setTextFormat(Qt.PlainText)
        self._scan_status.setWordWrap(True)
        self._scan_status.setFixedWidth(650)
        self._scan_status.hide()
        layout.addWidget(self._scan_status, 0, Qt.AlignHCenter)

        # Linux only: install usbmuxd / libimobiledevice (or start the daemon)
        # with the system's own password prompt.
        self._install_btn = QPushButton(
            QCoreApplication.translate("Nugget", "Install USB dependencies…"), self)
        self._install_btn.setCursor(Qt.PointingHandCursor)
        self._install_btn.clicked.connect(self._install_dependencies)
        self._install_btn.hide()
        layout.addWidget(self._install_btn, 0, Qt.AlignHCenter)

        self._continue_btn = QPushButton(
            QCoreApplication.translate("Nugget", "Continue without a device"), self)
        self._continue_btn.setCursor(Qt.PointingHandCursor)
        self._continue_btn.clicked.connect(self.window.continue_without_device)
        layout.addWidget(self._continue_btn, 0, Qt.AlignHCenter)

        self._retheme()
        self.refresh_dependency_hint()

    def refresh_dependency_hint(self, scan_failed: bool = False):
        """Show the install button when packages are missing, or when a scan
        failed while the usbmuxd service is down."""
        from src.devicemanagement import linux_deps
        status = linux_deps.check()
        self._install_btn.setVisible(
            status.can_fix and (bool(status.missing_packages) or (scan_failed and not status.daemon_running)))

    def _install_dependencies(self):
        from src.gui.dialogs.linux_deps_dialog import prompt_and_install
        prompt_and_install(self.window)
        self.refresh_dependency_hint()

    def _refresh(self):
        try:
            self.window.refresh_devices()
        except Exception as error:
            self.set_scan_status(str(error), busy=False)

    def set_scan_status(self, text, busy=False):
        self._scan_status.setText(text)
        self._fit_help_labels()
        self._scan_status.setVisible(bool(text))
        self._refresh_btn.setEnabled(not busy)
        self.refresh_dependency_hint(scan_failed=bool(text))

    def _fit_help_labels(self):
        # QLabel's default minimum hint may allow wrapped text to be clipped
        # instead of making the scroll content taller.
        for label in (self._steps, self._help_detail, self._scan_status):
            label.setMinimumHeight(max(0, label.heightForWidth(650)) + 4)

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self.setStyleSheet(t("page_bg"))
        self._scroll.setStyleSheet(t("scroll_area"))
        self._icon_lbl.setPixmap(theme_pixmap(
            ":/icon/phone.svg", c.text_secondary, self.ICON_PX,
            self.devicePixelRatioF()))
        self._title.setStyleSheet(t("home_title"))
        self._message.setStyleSheet(t("home_subtitle"))
        self._continue_btn.setStyleSheet(t("mini_button"))
        self._diagnostics_btn.setStyleSheet(t("mini_button"))
        self._logs_btn.setStyleSheet(t("mini_button"))
        self._steps.setStyleSheet(t("home_subtitle"))
        self._help_detail.setStyleSheet(t("home_subtitle"))
        self._scan_status.setStyleSheet(t("home_subtitle"))
        self._fit_help_labels()
