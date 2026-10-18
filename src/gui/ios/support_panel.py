from PySide6.QtCore import Qt, QSize, QUrl, QRectF, QCoreApplication
from PySide6.QtGui import QDesktopServices, QPixmap, QPainter, QPainterPath, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QToolButton, QSizePolicy,
)

from src.gui.credits import CREDITS
from src.gui.ios.components import IOSCard, IOSCollapsibleSection
from src.gui.theme import ColorThemeManager, theme_pixmap, t


def _tr(text):
    return QCoreApplication.translate("SupportPanel", text)


class SupportPanel(IOSCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        header = QVBoxLayout()
        header.setSpacing(12)
        heading = QVBoxLayout()
        heading.setSpacing(4)
        self.title = QLabel(_tr('Join for Support!'))
        self.title.setObjectName('supportTitle')
        heading.addWidget(self.title)
        self.subtitle = QLabel(_tr('GoldenNugget community & project'))
        self.subtitle.setObjectName('supportMuted')
        heading.addWidget(self.subtitle)
        header.addLayout(heading)
        self.discord = self._link_icon('Join the GoldenNugget Discord server', 'https://discord.gg/F7ssrHjdgK')
        self.github = self._link_icon('GoldenNugget on GitHub', 'https://github.com/GoldenNugget-Team/GoldenNugget')
        links = QHBoxLayout()
        links.setSpacing(8)
        links.addWidget(self.discord)
        links.addWidget(self.github)
        links.addStretch(1)
        header.addLayout(links)
        layout.addLayout(header)
        team = QHBoxLayout()
        team.setSpacing(12)
        portraits = (
            ":/credits/awesomenull.webp",
            ":/credits/windows11aero.webp",
            ":/credits/kik4311.png",
            ":/credits/LeminLimez.png",
        )
        for (role, name, url), portrait in zip(CREDITS[:len(portraits)], portraits):
            team.addWidget(self._profile(role, name, url, portrait), 1)
        layout.addLayout(team)
        credits = IOSCollapsibleSection(_tr('Contributors && acknowledgements'), expanded=False)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        for index, (role, name, url) in enumerate(CREDITS[len(portraits):]):
            grid.addWidget(self._credit(role, name, url), index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        credits.body_layout.addLayout(grid)
        layout.addWidget(credits)
        self._retheme()

    def _profile(self, role, name, url, portrait):
        tile = QWidget()
        column = QVBoxLayout(tile)
        column.setContentsMargins(8, 8, 8, 8)
        column.setSpacing(5)
        avatar = QToolButton()
        avatar.setFixedSize(60, 60)
        avatar.setIconSize(QSize(56, 56))
        avatar.setIcon(QIcon(self._portrait(portrait)))
        avatar.setObjectName('supportAvatar')
        avatar.setToolTip(f'{name} · {role}')
        avatar.setAccessibleName(f'{name} · {role}')
        avatar.setCursor(Qt.PointingHandCursor)
        avatar.clicked.connect(lambda _, link=url: QDesktopServices.openUrl(QUrl(link)))
        column.addWidget(avatar, 0, Qt.AlignHCenter)
        name_button = QPushButton(name)
        name_button.setObjectName('supportName')
        name_button.setCursor(Qt.PointingHandCursor)
        name_button.clicked.connect(lambda _, link=url: QDesktopServices.openUrl(QUrl(link)))
        column.addWidget(name_button)
        caption = QLabel(_tr(role))
        caption.setObjectName('supportMuted')
        caption.setWordWrap(True)
        caption.setAlignment(Qt.AlignCenter)
        column.addWidget(caption)
        column.addStretch()
        return tile

    @staticmethod
    def _credit(role, name, url):
        entry = QWidget()
        column = QVBoxLayout(entry)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        label = QLabel(_tr(role))
        label.setObjectName('supportMuted')
        column.addWidget(label)
        link = QLabel(f'<a href="{url}">{_tr(name)}</a>')
        link.setObjectName('supportCredit')
        link.setWordWrap(True)
        link.setOpenExternalLinks(True)
        column.addWidget(link)
        return entry


    def _link_icon(self, label, url):
        button = QToolButton()
        button.setObjectName('supportLink')
        button.setFixedSize(48, 48)
        button.setIconSize(QSize(26, 26))
        button.setToolTip(_tr(label))
        button.setAccessibleName(_tr(label))
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        return button

    @staticmethod
    def _portrait(resource):
        source = QPixmap(resource).scaled(
            112, 112, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        image = QPixmap(112, 112)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        mask = QPainterPath()
        mask.addEllipse(QRectF(0, 0, 112, 112))
        painter.setClipPath(mask)
        painter.drawPixmap((112 - source.width()) // 2, (112 - source.height()) // 2, source)
        painter.end()
        image.setDevicePixelRatio(2)
        return image

    def _retheme(self):
        super()._retheme()
        if not hasattr(self, 'discord'):
            return
        c = ColorThemeManager.instance().colors
        self.setStyleSheet(self.styleSheet() + t("support_panel"))
        self.discord.setIcon(QIcon(theme_pixmap(':/icon/discord.svg', '#5865F2', 26, self.devicePixelRatioF())))
        self.github.setIcon(QIcon(theme_pixmap(':/icon/github.svg', c.text_primary, 26, self.devicePixelRatioF())))
