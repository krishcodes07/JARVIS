"""Theme tokens and color palettes for the JARVIS GUI."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Theme:
    """Design system color tokens."""

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
