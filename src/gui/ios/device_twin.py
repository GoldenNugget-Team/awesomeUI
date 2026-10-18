"""Digital twin: the selected tweaks drawn on a full Lock Screen and Home Screen.

Works on preset-shaped data (``{"TweakName": {"enabled": ..., "value": ...}}``)
so the same picture is available for the current selection, a saved preset and
a setup someone shared as a code. Only tweaks with a visible result are drawn;
the rest are counted so the preview never pretends to show everything.

It is a drawing, not a screenshot: geometry follows an iPhone 15 Pro in points
(393 x 852), wallpapers come from a .tendies preview when one is available, and
stock apps are stylised tiles.
"""
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QCoreApplication, QT_TRANSLATE_NOOP, QDate, QLocale, QPointF, QRectF, QSize, Qt, QTime
from PySide6.QtGui import (
    QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.gui.ios.statusbar_preview import (
    DEVICE_PT_W, StatusBarPreviewState, paint_status_bar, preview_state,
)
from src.gui.theme import ColorThemeManager

CONTEXT = "DeviceTwin"
DEVICE_PT_H = 852.0
# Home-button iPhones still supported by iOS 26 (SE 2nd and 3rd generation).
_HOME_BUTTON_MODELS = frozenset({"iPhone12,8", "iPhone14,6"})


def _tr(text):
    return QCoreApplication.translate(CONTEXT, text)


@dataclass
class TwinApp:
    name: str
    color: str = "#888888"
    glyph: str = ""
    image: Optional[str] = None      # icon theme PNG
    show_label: bool = True
    kind: str = ""                   # "clock" / "calendar" draw live faces


@dataclass
class TwinState:
    status: StatusBarPreviewState
    cutout: str = "island"           # island / notch / none
    home_button: bool = False
    footnote: str = ""
    supervised: bool = False
    glass_clock: bool = True
    glass_dock: bool = True
    glass_icons: bool = True
    search_button: bool = True
    seconds_hand: bool = True
    rtl: bool = False
    build_label: str = ""
    themed: list = field(default_factory=list)
    wallpaper: Optional[str] = None  # image file
    shown: list = field(default_factory=list)    # translated effect names
    not_shown: int = 0


# Tweaks the twin can draw, with the legend text for each.
VISIBLE = {
    "StatusBar": QT_TRANSLATE_NOOP("DeviceTwin", "Status bar overrides"),
    "HideDICompletely": QT_TRANSLATE_NOOP("DeviceTwin", "Dynamic Island turned off"),
    "LockScreenFootnote": QT_TRANSLATE_NOOP("DeviceTwin", "Lock Screen footnote"),
    "SBShowSupervisionTextOnLockScreen": QT_TRANSLATE_NOOP("DeviceTwin", "Supervision text"),
    "NoLiquidClock": QT_TRANSLATE_NOOP("DeviceTwin", "Solid Lock Screen clock"),
    "NoLiquidDock": QT_TRANSLATE_NOOP("DeviceTwin", "Solid Dock"),
    "UseFlatIconsEverywhere": QT_TRANSLATE_NOOP("DeviceTwin", "Flat icons"),
    "SBHideSearchAffordance": QT_TRANSLATE_NOOP("DeviceTwin", "Search button hidden"),
    "DisableSecondsHand": QT_TRANSLATE_NOOP("DeviceTwin", "Clock icon without seconds hand"),
    "SBBuildNumber": QT_TRANSLATE_NOOP("DeviceTwin", "Build number in the status bar"),
    "RTL": QT_TRANSLATE_NOOP("DeviceTwin", "Right-to-left layout"),
    "IconThemes": QT_TRANSLATE_NOOP("DeviceTwin", "Custom icons"),
    "PosterBoard": QT_TRANSLATE_NOOP("DeviceTwin", "Wallpaper"),
}

def _cutout_for(model: str, version: str) -> tuple:
    from src.devicemanagement.device_capabilities import has_dynamic_island
    model = str(model or "")
    if model in _HOME_BUTTON_MODELS:
        return "none", True
    if has_dynamic_island(model) or not model.startswith("iPhone"):
        return "island", False
    return "notch", False


def _effective(name, entry, version, model) -> bool:
    """Selected and able to run on this device (incompatible tweaks do nothing)."""
    from src.controllers.risk_assessment import is_selected
    from src.gui.ios.compat import compatibility_reasons
    from src.tweaks.tweak_names import TweakID
    if not is_selected(name, entry):
        return False
    if not version:
        return True
    try:
        return not compatibility_reasons(TweakID[name], version, model)
    except KeyError:
        return True


def _status_state(entry, version) -> StatusBarPreviewState:
    from src.tweaks.status_bar.status_bar_tweak import StatusBarTweak
    from src.controllers.preset_manager import PresetManager
    tweak = StatusBarTweak()
    if isinstance(entry, dict):
        PresetManager.__new__(PresetManager)._apply_status_bar(tweak, entry)
    ios27 = False
    try:
        ios27 = int(str(version).split(".")[0]) >= 27
    except ValueError:
        pass
    return preview_state(tweak, ios27)


def build_state(tweaks_data, version="", model="", build="", wallpaper=None) -> TwinState:
    """What the device would look like with ``tweaks_data`` applied."""
    from src.controllers.risk_assessment import is_selected
    data = tweaks_data or {}
    on = {name for name, entry in data.items() if _effective(name, entry, version, model)}
    cutout, home_button = _cutout_for(model, version)
    state = TwinState(status=_status_state(data.get("StatusBar"), version),
                      cutout=cutout, home_button=home_button)
    if "HideDICompletely" in on and cutout == "island":
        state.cutout = "none"
    if "LockScreenFootnote" in on:
        state.footnote = str(data["LockScreenFootnote"].get("value") or "")
    state.supervised = "SBShowSupervisionTextOnLockScreen" in on
    state.glass_clock = "NoLiquidClock" not in on
    state.glass_dock = "NoLiquidDock" not in on
    state.glass_icons = "UseFlatIconsEverywhere" not in on
    state.search_button = "SBHideSearchAffordance" not in on
    state.seconds_hand = "DisableSecondsHand" not in on
    state.rtl = "RTL" in on
    if "SBBuildNumber" in on:
        state.build_label = build or _tr("Build")
    for theme in (data.get("IconThemes") or {}).get("themes", []) if "IconThemes" in on else []:
        if isinstance(theme, dict):
            label = str(theme.get("display_name") or "")
            state.themed.append(TwinApp(label, image=theme.get("icon_path") or None,
                                        show_label=bool(label)))
    if wallpaper:
        state.wallpaper = wallpaper
        on.add("PosterBoard")
    stock = _status_state(None, version)
    stock.time = state.status.time
    if "StatusBar" in on and state.status == stock:
        on.discard("StatusBar")   # switched on without any override
    shown = [name for name in VISIBLE if name in on]
    state.shown = [_tr(VISIBLE[name]) for name in shown]
    state.not_shown = sum(1 for name, entry in data.items()
                          if name not in VISIBLE and is_selected(name, entry))
    return state


def current_wallpaper() -> Optional[str]:
    """Preview image of the first queued PosterBoard wallpaper, if it can be made."""
    try:
        from src.controllers.tendie_preview import extract_tendie_preview
        from src.tweaks.tweaks import tweaks, TweakID
        board = tweaks.get(TweakID.PosterBoard)
        for item in getattr(board, "tendies", [])[:1]:
            if getattr(item, "path", None):
                return extract_tendie_preview(item.path)
    except Exception:
        return None
    return None


# --- painting -------------------------------------------------------------

_STOCK = (
    (QT_TRANSLATE_NOOP("DeviceTwin", "FaceTime"), "#34C759", "▶"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Calendar"), "#FFFFFF", "", "calendar"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Photos"), "#FFFFFF", "✿"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Camera"), "#8E8E93", "◉"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Mail"), "#1E90FF", "✉"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Notes"), "#FFD60A", "≡"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Reminders"), "#FFFFFF", "☰"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Clock"), "#000000", "", "clock"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Weather"), "#2F7DE1", "☀"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Maps"), "#5AC85A", "➤"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Music"), "#FA2D48", "♫"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Settings"), "#8E8E93", "⚙"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "App Store"), "#0A84FF", "A"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Wallet"), "#1C1C1E", "▤"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Health"), "#FFFFFF", "♥"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Files"), "#0A84FF", "▢"),
)
_DOCK = (
    (QT_TRANSLATE_NOOP("DeviceTwin", "Phone"), "#34C759", "✆"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Safari"), "#0A84FF", "◎"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Messages"), "#34C759", "✉"),
    (QT_TRANSLATE_NOOP("DeviceTwin", "Music"), "#FA2D48", "♫"),
)


def _font(px, weight=QFont.Weight.DemiBold):
    font = QFont()
    font.setPixelSize(max(1, round(px)))
    font.setWeight(weight)
    return font


def _app(entry):
    name, color, glyph, *kind = entry
    return TwinApp(name, color, glyph, kind=kind[0] if kind else "")


def _paint_wallpaper(p, screen, state, images):
    image = images.get(state.wallpaper) if state.wallpaper else None
    if image is not None and not image.isNull():
        scaled = image.scaled(screen.size().toSize(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                              Qt.TransformationMode.SmoothTransformation)
        p.drawImage(QPointF(screen.center().x() - scaled.width() / 2,
                            screen.center().y() - scaled.height() / 2), scaled)
        return
    gradient = QLinearGradient(screen.topLeft(), screen.bottomRight())
    gradient.setColorAt(0.0, QColor(0x2B, 0x3A, 0x67))
    gradient.setColorAt(0.55, QColor(0x5B, 0x3F, 0x84))
    gradient.setColorAt(1.0, QColor(0xC0, 0x5A, 0x7A))
    p.fillRect(screen, gradient)


def _glass(p, rect, radius, s, strong=True):
    """Liquid Glass approximation: translucent fill, bright rim, top highlight."""
    p.setPen(QPen(QColor(255, 255, 255, 120 if strong else 70), 1.0 * s))
    p.setBrush(QColor(255, 255, 255, 46 if strong else 30))
    p.drawRoundedRect(rect, radius, radius)
    shine = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    shine.setColorAt(0.0, QColor(255, 255, 255, 70))
    shine.setColorAt(0.45, QColor(255, 255, 255, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(shine)
    p.drawRoundedRect(rect, radius, radius)


def _paint_icon(p, rect, app, s, glass, images, seconds_hand=True, now=None):
    radius = rect.width() * 0.225
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.save()
    p.setClipPath(path)
    image = images.get(app.image) if app.image else None
    if image is not None and not image.isNull():
        p.drawImage(rect, image)
    else:
        p.fillPath(path, QColor(app.color))
        light = QColor(app.color).lightness() > 200
        ink = QColor(0x1C, 0x1C, 0x1E) if light else QColor(255, 255, 255)
        if app.kind == "clock":
            _paint_clock_face(p, rect, s, seconds_hand, now or QTime.currentTime())
        elif app.kind == "calendar":
            p.setPen(QColor(0xFF, 0x3B, 0x30))
            p.setFont(_font(rect.height() * 0.17, QFont.Weight.Bold))
            p.drawText(QRectF(rect.left(), rect.top() + rect.height() * 0.08, rect.width(), rect.height() * 0.22),
                       Qt.AlignmentFlag.AlignCenter, QLocale().toString(QDate.currentDate(), "ddd").upper())
            p.setPen(ink)
            p.setFont(_font(rect.height() * 0.5, QFont.Weight.Normal))
            p.drawText(QRectF(rect.left(), rect.top() + rect.height() * 0.28, rect.width(), rect.height() * 0.62),
                       Qt.AlignmentFlag.AlignCenter, str(QDate.currentDate().day()))
        else:
            p.setPen(ink)
            p.setFont(_font(rect.height() * 0.46, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, app.glyph)
    if glass:
        shine = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        shine.setColorAt(0.0, QColor(255, 255, 255, 95))
        shine.setColorAt(0.5, QColor(255, 255, 255, 0))
        p.fillPath(path, shine)
    p.restore()
    if glass:
        p.setPen(QPen(QColor(255, 255, 255, 110), 0.9 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


def _paint_clock_face(p, rect, s, seconds_hand, now):
    import math
    c = rect.center()
    r = rect.width() * 0.42
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(c, r, r)
    p.setPen(QPen(QColor(0x1C, 0x1C, 0x1E), 0.8 * s))
    for i in range(12):
        a = math.radians(i * 30)
        p.drawLine(QPointF(c.x() + math.sin(a) * r * 0.82, c.y() - math.cos(a) * r * 0.82),
                   QPointF(c.x() + math.sin(a) * r * 0.95, c.y() - math.cos(a) * r * 0.95))

    def hand(angle, length, width, color):
        a = math.radians(angle)
        p.setPen(QPen(QColor(color), width * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(c, QPointF(c.x() + math.sin(a) * r * length, c.y() - math.cos(a) * r * length))

    hand((now.hour() % 12 + now.minute() / 60) * 30, 0.5, 2.6, "#1C1C1E")
    hand(now.minute() * 6, 0.75, 2.0, "#1C1C1E")
    if seconds_hand:
        hand(now.second() * 6, 0.85, 0.9, "#FF9500")


def _paint_frame(p, rect, s, state):
    """Phone body; returns the screen rect."""
    body = QPainterPath()
    body.addRoundedRect(rect, 60 * s, 60 * s)
    p.fillPath(body, QColor(0x2C, 0x2C, 0x2E))
    inner = QPainterPath()
    inner.addRoundedRect(rect.adjusted(2 * s, 2 * s, -2 * s, -2 * s), 58 * s, 58 * s)
    p.fillPath(inner, QColor(0x0B, 0x0B, 0x0C))
    bezel = 10 * s
    if state.home_button:
        screen = QRectF(rect.left() + bezel * 1.6, rect.top() + 88 * s,
                        rect.width() - bezel * 3.2, rect.height() - 176 * s)
        p.setPen(QPen(QColor(0x5A, 0x5A, 0x5E), 2 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(rect.center().x(), rect.bottom() - 44 * s), 26 * s, 26 * s)
        return screen, 0.0
    return rect.adjusted(bezel, bezel, -bezel, -bezel), 50 * s


def paint_lock_screen(p, screen, s, state, images):
    _paint_wallpaper(p, screen, state, images)
    paint_status_bar(p, screen, state.status, True, cutout=state.cutout)
    date = QLocale().toString(QDate.currentDate(), "dddd, d MMMM")
    p.setPen(QColor(255, 255, 255, 225))
    p.setFont(_font(17 * s))
    p.drawText(QRectF(screen.left(), screen.top() + 66 * s, screen.width(), 24 * s),
               Qt.AlignmentFlag.AlignCenter, date)
    clock_rect = QRectF(screen.left(), screen.top() + 84 * s, screen.width(), 112 * s)
    time = QTime.currentTime().toString("H:mm")
    font = _font(100 * s, QFont.Weight.Bold)
    if state.glass_clock:
        path = QPainterPath()
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance(time)
        path.addText(QPointF(clock_rect.center().x() - width / 2, clock_rect.bottom() - 18 * s), font, time)
        fill = QLinearGradient(clock_rect.topLeft(), clock_rect.bottomLeft())
        fill.setColorAt(0.0, QColor(255, 255, 255, 150))
        fill.setColorAt(1.0, QColor(255, 255, 255, 60))
        p.setPen(QPen(QColor(255, 255, 255, 210), 1.4 * s))
        p.setBrush(fill)
        p.drawPath(path)
    else:
        p.setPen(QColor(255, 255, 255))
        p.setFont(font)
        p.drawText(clock_rect, Qt.AlignmentFlag.AlignCenter, time)

    bottom = screen.bottom() - (34 * s if not state.home_button else 12 * s)
    lines = []
    if state.supervised:
        lines.append(_tr("This iPhone is supervised and managed."))
    if state.footnote:
        lines.append(state.footnote)
    if lines:
        p.setPen(QColor(255, 255, 255, 230))
        p.setFont(_font(12 * s, QFont.Weight.Medium))
        text_rect = QRectF(screen.left() + 70 * s, bottom - 96 * s, screen.width() - 140 * s, 40 * s)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
                   | Qt.TextFlag.TextWordWrap, "\n".join(lines))
    if not state.home_button:
        for cx in (screen.left() + 64 * s, screen.right() - 64 * s):
            circle = QRectF(cx - 25 * s, bottom - 62 * s, 50 * s, 50 * s)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawEllipse(circle)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawRoundedRect(QRectF(screen.center().x() - 67 * s, screen.bottom() - 13 * s, 134 * s, 5 * s),
                          2.5 * s, 2.5 * s)


def paint_home_screen(p, screen, s, state, images):
    _paint_wallpaper(p, screen, state, images)
    status = state.status
    if state.build_label:
        status = StatusBarPreviewState(**{**status.__dict__, "time": state.build_label})
    paint_status_bar(p, screen, status, False, cutout=state.cutout)
    apps = [_app(entry) for entry in _STOCK] + list(state.themed)
    apps = apps[:24]
    icon = 62 * s
    margin = 27 * s
    gap = (screen.width() - 2 * margin - 4 * icon) / 3
    top = screen.top() + 72 * s
    label_font = _font(11.5 * s, QFont.Weight.Medium)
    for index, app in enumerate(apps):
        row, col = divmod(index, 4)
        if state.rtl:
            col = 3 - col
        rect = QRectF(screen.left() + margin + col * (icon + gap), top + row * 94 * s, icon, icon)
        _paint_icon(p, rect, app, s, state.glass_icons, images, state.seconds_hand)
        if app.show_label:
            p.setPen(QColor(255, 255, 255))
            p.setFont(label_font)
            name = _tr(app.name) if not app.image else app.name
            p.drawText(QRectF(rect.left() - gap / 2, rect.bottom() + 4 * s, icon + gap, 16 * s),
                       Qt.AlignmentFlag.AlignHCenter,
                       QFontMetricsF(label_font).elidedText(name, Qt.TextElideMode.ElideRight, icon + gap))

    dock_h = 92 * s
    dock = QRectF(screen.left() + 12 * s, screen.bottom() - dock_h - (20 * s if not state.home_button else 6 * s),
                  screen.width() - 24 * s, dock_h)
    if state.search_button:
        pill = QRectF(screen.center().x() - 44 * s, dock.top() - 42 * s, 88 * s, 30 * s)
        _glass(p, pill, 15 * s, s, strong=False)
        p.setPen(QColor(255, 255, 255, 235))
        p.setFont(_font(13 * s, QFont.Weight.DemiBold))
        p.drawText(pill, Qt.AlignmentFlag.AlignCenter, "⌕ " + _tr("Search"))
    if state.glass_dock:
        _glass(p, dock, 34 * s, s)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0x3A, 0x3A, 0x3C, 215))
        p.drawRoundedRect(dock, 34 * s, 34 * s)
    dock_apps = [_app(entry) for entry in _DOCK]
    if state.rtl:
        dock_apps.reverse()
    step = (dock.width() - 4 * icon) / 5
    for index, app in enumerate(dock_apps):
        rect = QRectF(dock.left() + step + index * (icon + step), dock.center().y() - icon / 2, icon, icon)
        _paint_icon(p, rect, app, s, state.glass_icons, images, state.seconds_hand)
    if not state.home_button:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawRoundedRect(QRectF(screen.center().x() - 67 * s, screen.bottom() - 13 * s, 134 * s, 5 * s),
                          2.5 * s, 2.5 * s)


class DeviceTwinView(QWidget):
    """Lock Screen and Home Screen side by side, each in a full phone frame."""

    GAP = 28
    LABEL_H = 26

    def __init__(self, state: TwinState, parent=None):
        super().__init__(parent)
        self._images = {}
        self.set_state(state)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(policy)
        self.setAccessibleName(_tr("iPhone preview"))

    def set_state(self, state: TwinState):
        self.state = state
        self._images = {}
        for path in [state.wallpaper] + [app.image for app in state.themed]:
            if path and path not in self._images:
                self._images[path] = QImage(path)
        self.update()

    def sizeHint(self):
        return QSize(640, 700)

    def minimumSizeHint(self):
        return QSize(360, 420)

    def _phone_rect(self, index):
        frame_w = DEVICE_PT_W + 20
        frame_h = DEVICE_PT_H + 20
        avail_h = self.height() - self.LABEL_H
        scale = min((self.width() - self.GAP) / (2 * frame_w), avail_h / frame_h)
        w, h = frame_w * scale, frame_h * scale
        x0 = (self.width() - (2 * w + self.GAP)) / 2
        return QRectF(x0 + index * (w + self.GAP), 0, w, h), scale

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        colors = ColorThemeManager.instance().colors
        titles = (QCoreApplication.translate("Nugget", "Lock Screen"),
                  QCoreApplication.translate("Nugget", "Home Screen"))
        for index, painter in enumerate((paint_lock_screen, paint_home_screen)):
            rect, s = self._phone_rect(index)
            screen, radius = _paint_frame(p, rect, s, self.state)
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(screen, radius, radius)
            p.setClipPath(clip)
            painter(p, screen, s, self.state, self._images)
            p.restore()
            p.setPen(QColor(colors.text_secondary))
            p.setFont(_font(13, QFont.Weight.Medium))
            p.drawText(QRectF(rect.left(), rect.bottom() + 6, rect.width(), self.LABEL_H - 6),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, titles[index])
        p.end()
