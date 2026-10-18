from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton
)

from src.gui.ios.components import (
    IOSSectionHeader, IOSCard, IOSPrimaryButton, IOSDangerButton)
from src.gui.theme import ColorThemeManager, t


class IOSApplyPage(QWidget):
    """Apply / Remove tweaks — rebuilt from the classic Apply page using the
    iOS-style components."""
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("iosContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        c = ColorThemeManager.instance().colors
        scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        self._scroll = scroll
        content = QWidget()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 32)
        content_layout.setSpacing(8)

        # --- Apply ---
        content_layout.addWidget(IOSSectionHeader(
            QCoreApplication.translate("Nugget", "Apply Tweaks")))

        apply_card = IOSCard()
        apply_layout = QVBoxLayout(apply_card)
        apply_layout.setContentsMargins(16, 12, 16, 12)
        apply_layout.setSpacing(8)

        apply_desc = QLabel(QCoreApplication.translate(
            "Nugget",
            "Applies every enabled tweak to your device. The device reboots "
            "when done. If you turn Find My off for this apply, turn it back "
            "on afterwards."))
        apply_desc.setWordWrap(True)
        apply_desc.setStyleSheet(f"color: {c.text_secondary}; font-size: 13px; background-color: transparent;")
        self.apply_desc = apply_desc
        apply_layout.addWidget(apply_desc)

        self.apply_btn = IOSPrimaryButton(QCoreApplication.translate(
            "Nugget", "Apply Tweaks"))
        self.apply_btn.setToolTip(QCoreApplication.translate(
            "Nugget", "Apply all enabled tweaks and restart the device."))
        self.apply_btn.setAccessibleName(QCoreApplication.translate(
            "Nugget", "Apply enabled tweaks"))
        self.apply_btn.clicked.connect(self.window.apply_tweaks_clicked)
        apply_layout.addWidget(self.apply_btn)
        self.preview_btn = QPushButton(QCoreApplication.translate(
            "DeviceTwin", "Preview on iPhone"))
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.setToolTip(QCoreApplication.translate(
            "DeviceTwin", "See the Lock Screen and Home Screen with the selected tweaks before applying."))
        self.preview_btn.clicked.connect(self.window.show_device_twin)
        apply_layout.addWidget(self.preview_btn)
        self.preview_btn.setStyleSheet(t("mini_button"))
        content_layout.addWidget(apply_card)

        # --- Remove ---
        content_layout.addWidget(IOSSectionHeader(
            QCoreApplication.translate("Nugget", "Restore Defaults")))

        remove_card = IOSCard()
        remove_layout = QVBoxLayout(remove_card)
        remove_layout.setContentsMargins(16, 12, 16, 12)
        remove_layout.setSpacing(8)

        remove_desc = QLabel(QCoreApplication.translate(
            "Nugget",
            "Restores the original values for the tweak pages you pick."))
        remove_desc.setWordWrap(True)
        remove_desc.setStyleSheet(f"color: {c.text_secondary}; font-size: 13px; background-color: transparent;")
        self.remove_desc = remove_desc
        remove_layout.addWidget(remove_desc)

        self.remove_btn = IOSDangerButton(QCoreApplication.translate(
            "Nugget", "Restore Defaults"))
        self.remove_btn.setToolTip(QCoreApplication.translate(
            "Nugget", "Restore the stock values for the selected tweak pages."))
        self.remove_btn.setAccessibleName(QCoreApplication.translate(
            "Nugget", "Restore defaults for selected sections"))
        self.remove_btn.clicked.connect(self.window.remove_tweaks_clicked)
        remove_layout.addWidget(self.remove_btn)
        content_layout.addWidget(remove_card)

        from src.gui.ios.restore_progress import RestoreProgressCard
        self.progress_card = RestoreProgressCard(self)
        self._busy = False
        self.status_lbl = self.progress_card.status_label
        self.progress_bar = self.progress_card.bar
        content_layout.addWidget(self.progress_card)

        from src.gui.ios.operation_result import OperationResultCard
        self.result_card = OperationResultCard(
            self.window.ios_home.open_logs, self.window.dismiss_operation_result)
        content_layout.addWidget(self.result_card)

        content_layout.addStretch()

    def set_status(self, text: str):
        if text:
            self.progress_card.set_status(text)
        elif not self._busy:
            self.progress_card.hide()

    def set_stage(self, stage, category=""):
        self.progress_card.set_stage(stage, category)

    def set_busy(self, busy: bool):
        if busy and not self._busy:
            protective = self.window.device_manager.get_current_device_partially_supported()
            preferences = self.window.device_manager.pref_manager
            self.progress_card.start(protective,
                                     preferences.auto_reboot or preferences.skip_setup)
            self.progress_card.show()
        self._busy = busy
        connected = bool(self.window.device_manager.get_current_device_udid())
        self.apply_btn.setEnabled(not busy and connected)
        self.remove_btn.setEnabled(not busy and connected)

    def _retheme(self):
        c = ColorThemeManager.instance().colors
        self._scroll.setStyleSheet(f"background-color: {c.bg_primary}; border: none;")
        self.preview_btn.setStyleSheet(t("mini_button"))
        self.apply_desc.setStyleSheet(f"color: {c.text_secondary}; font-size: 13px; background-color: transparent;")
        self.remove_desc.setStyleSheet(f"color: {c.text_secondary}; font-size: 13px; background-color: transparent;")
        self.progress_card._retheme()
