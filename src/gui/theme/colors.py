from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ThemeColors:
    """All named color slots used across the application."""

    # Surfaces
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_input: str
    bg_elevated: str

    # Text
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_inverse: str

    # Accent
    accent: str
    accent_hover: str
    accent_pressed: str

    # Semantic
    success: str
    error: str
    error_hover: str
    error_pressed: str
    warning: str

    # Borders / dividers
    border: str
    divider: str

    # Interactive
    scrollbar: str
    scrollbar_pressed: str
    selection: str

    # Special
    card_border: str
    surface_hover: str
    danger_text: str

    def with_accent(self, accent: str, hover: str, pressed: str) -> "ThemeColors":
        return replace(self, accent=accent, accent_hover=hover, accent_pressed=pressed,
                       selection=accent)


# ---------------------------------------------------------------------------
# Dark palette (matches the current hardcoded colors exactly)
# ---------------------------------------------------------------------------
DARK = ThemeColors(
    bg_primary="#1e1e1e",
    bg_secondary="#1C1C1E",
    bg_tertiary="#2C2C2E",
    bg_input="#1C1C1E",
    bg_elevated="#1e1e1e",

    text_primary="#FFFFFF",
    text_secondary="#8E8E93",
    text_disabled="#787878",
    text_inverse="#FFFFFF",

    accent="#007AFF",
    accent_hover="#0066CC",
    accent_pressed="#0055AA",

    success="#30D158",
    error="#FF453A",
    error_hover="#FF5A50",
    error_pressed="#C2322A",
    warning="#FFD60A",

    border="#3A3A3C",
    divider="#3A3A3C",

    scrollbar="#3b3b3b",
    scrollbar_pressed="#535353",
    selection="#007AFF",

    card_border="#3A3A3C",
    surface_hover="#2C2C2E",
    danger_text="#FF453A",
)


# Light surfaces have distinct page/card/input levels, with dark secondary
# text and semantic colors that remain readable on every light surface.
LIGHT = ThemeColors(
    bg_primary="#F3F4F7",
    bg_secondary="#FFFFFF",
    bg_tertiary="#E9ECF2",
    bg_input="#FFFFFF",
    bg_elevated="#FFFFFF",
    text_primary="#181C25",
    text_secondary="#515A6B",
    text_disabled="#747C8B",
    text_inverse="#FFFFFF",
    accent="#005FC7",
    accent_hover="#0054B0",
    accent_pressed="#004999",
    success="#147437",
    error="#BC2629",
    error_hover="#AB2024",
    error_pressed="#941B20",
    warning="#775800",
    border="#B3BAC7",
    divider="#D0D5DF",
    scrollbar="#C7CDD8",
    scrollbar_pressed="#9CA6B7",
    selection="#005FC7",
    card_border="#D0D5DF",
    surface_hover="#E3E7EF",
    danger_text="#BC2629",
)


# ---------------------------------------------------------------------------
# Accent presets: (normal, hover, pressed)
# ---------------------------------------------------------------------------
ACCENT_PRESETS = {
    "blue":     ("#007AFF", "#0066CC", "#0055AA"),
    "purple":   ("#AF52DE", "#9B47C4", "#893DAB"),
    "pink":     ("#FF2D55", "#E6284D", "#CC2244"),
    "red":      ("#FF3B30", "#E6352B", "#CC2F26"),
    "orange":   ("#FF9500", "#E68600", "#CC7700"),
    "yellow":   ("#FFCC00", "#E6B800", "#CCA300"),
    "green":    ("#34C759", "#2EAF4E", "#289944"),
    "teal":     ("#5AC8FA", "#50B4E6", "#46A0D2"),
}

# Same hue choices as the dark palette, tuned for readable links and white
# button labels in light mode (including the yellow/orange/teal choices).
LIGHT_ACCENT_PRESETS = {
    "blue":   ("#005FC7", "#0054B0", "#004999"),
    "purple": ("#8438AD", "#733098", "#632985"),
    "pink":   ("#B91949", "#A41640", "#901238"),
    "red":    ("#BC2629", "#AB2024", "#941B20"),
    "orange": ("#984800", "#843E00", "#713500"),
    "yellow": ("#715700", "#624B00", "#533F00"),
    "green":  ("#147437", "#10652F", "#0D5628"),
    "teal":   ("#00657F", "#00586F", "#004B60"),
}
