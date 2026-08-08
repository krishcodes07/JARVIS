"""Theme tokens and application stylesheet generation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_soft: str
    danger: str = "#ff718d"

    @property
    def accent_color(self) -> QColor:
        return QColor(self.accent)


THEMES: dict[str, Theme] = {
    "Midnight": Theme(
        name="Midnight",
        background="#080b10",
        surface="#0d1219",
        surface_alt="#131a23",
        border="#222c39",
        text="#e7ecf3",
        muted="#8b97a8",
        accent="#5b9df5",
        accent_soft="#1d385a",
    ),
    "Obsidian": Theme(
        name="Obsidian",
        background="#0a0a0c",
        surface="#111114",
        surface_alt="#18181d",
        border="#2a2a31",
        text="#eeeeF2",
        muted="#92929e",
        accent="#8e80e8",
        accent_soft="#353052",
    ),
    "Aurora": Theme(
        name="Aurora",
        background="#07100f",
        surface="#0c1816",
        surface_alt="#12221f",
        border="#253d38",
        text="#e7f0ee",
        muted="#8ba09c",
        accent="#55bda9",
        accent_soft="#234b43",
    ),
}

ACCENTS: dict[str, str] = {
    "Electric Blue": "#5b9df5",
    "Arc Violet": "#8e80e8",
    "Plasma Cyan": "#56b8c7",
    "Reactor Green": "#62b98d",
    "Solar Amber": "#d7a455",
}


def get_theme(name: str, accent_name: str) -> Theme:
    base = THEMES.get(name, THEMES["Midnight"])
    accent = ACCENTS.get(accent_name, base.accent)
    soft = QColor(accent).darker(190).name()
    return replace(base, accent=accent, accent_soft=soft)


def build_stylesheet(theme: Theme) -> str:
    """Return the global QSS; custom widgets still paint their own glow effects."""

    return f"""
        QWidget {{
            color: {theme.text};
            font-family: "Segoe UI";
            font-size: 13px;
        }}
        QMainWindow, QWidget#AppRoot {{
            background: {theme.background};
        }}
        QFrame#AppFrame {{
            background: {theme.background};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        QFrame#Drawer {{
            background: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        QFrame#SettingsCard {{
            background: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        QFrame#ResponseCard {{
            background: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        QLabel#BrandSmall {{
            color: {theme.accent};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
        }}
        QLabel#DrawerTitle, QLabel#SettingsTitle {{
            font-size: 17px;
            font-weight: 600;
        }}
        QLabel#SectionLabel {{
            color: {theme.muted};
            font-size: 11px;
            font-weight: 650;
        }}
        QLabel#ResponseLabel {{
            color: {theme.text};
            font-size: 14px;
        }}
        QLabel#StatusLabel {{
            color: {theme.muted};
            font-size: 12px;
        }}
        QLabel#SettingsPageTitle {{
            color: {theme.text};
            font-size: 24px;
            font-weight: 600;
        }}
        QLabel#SettingsPageSubtitle,
        QLabel#SettingsCardDescription {{
            color: {theme.muted};
            font-size: 12px;
        }}
        QLabel#SettingsCardTitle {{
            color: {theme.text};
            font-size: 15px;
            font-weight: 600;
        }}
        QLabel#SettingsFieldLabel {{
            color: {theme.muted};
            font-size: 11px;
            font-weight: 600;
        }}
        QLabel#SettingsValue {{
            color: {theme.muted};
            font-size: 11px;
        }}
        QLabel#SettingsStatus {{
            color: {theme.accent};
            font-size: 12px;
        }}
        QScrollArea#SettingsScroll,
        QWidget#SettingsContent,
        QWidget#SettingsPage {{
            background: transparent;
            border: none;
        }}
        QPushButton#DrawerAction {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 10px 12px;
            text-align: left;
            color: {theme.muted};
        }}
        QPushButton#DrawerAction:hover {{
            color: {theme.text};
            background: {theme.surface_alt};
            border-color: {theme.border};
        }}
        QPushButton#PrimaryAction {{
            background: {theme.surface_alt};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 9px;
            padding: 10px 14px;
            font-weight: 600;
        }}
        QPushButton#PrimaryAction:hover {{
            color: {theme.accent};
            border-color: {theme.accent};
        }}
        QPushButton#QuietAction {{
            background: {theme.surface_alt};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 9px;
            padding: 9px 12px;
        }}
        QComboBox {{
            background: {theme.surface_alt};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 8px;
            padding: 8px 10px;
            min-height: 18px;
        }}
        QComboBox:hover, QComboBox:focus {{ border-color: {theme.accent}; }}
        QComboBox QAbstractItemView {{
            background: {theme.surface};
            color: {theme.text};
            selection-background-color: {theme.accent_soft};
            border: 1px solid {theme.border};
        }}
        QSlider::groove:horizontal {{
            height: 4px;
            background: {theme.surface_alt};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {theme.accent};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 14px;
            height: 14px;
            margin: -5px 0;
            background: {theme.text};
            border: 2px solid {theme.accent};
            border-radius: 7px;
        }}
        QToolTip {{
            background: {theme.surface_alt};
            color: {theme.text};
            border: 1px solid {theme.border};
            padding: 5px;
        }}
        QScrollArea#ConversationView, QWidget#TranscriptContent {{
            background: transparent;
            border: none;
        }}
        QListWidget#ConversationList {{
            background: transparent;
            border: none;
            outline: none;
            color: {theme.muted};
        }}
        QListWidget#ConversationList::item {{
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 9px 10px;
        }}
        QListWidget#ConversationList::item:hover {{
            color: {theme.text};
            background: {theme.surface_alt};
            border-color: {theme.border};
        }}
        QListWidget#ConversationList::item:selected {{
            color: {theme.text};
            background: {theme.surface_alt};
            border-color: {theme.accent};
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 7px;
            margin: 2px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.border};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.accent_soft};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
    """
