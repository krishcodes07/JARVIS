"""Glowing icon button widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import QPushButton, QWidget

if TYPE_CHECKING:
    from jarvis.ui.gui.themes import Theme


class GlowIconButton(QPushButton):
    """Icon button with glowing active and hover states."""

    def __init__(
        self,
        icon_name: str,
        theme: Theme,
        size: int = 46,
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self.theme = theme
        self.button_size = size
        self.setCheckable(checkable)
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_symbol()
        self.set_theme(theme)

    def _update_symbol(self) -> None:
        symbols = {
            "menu": "☰",
            "settings": "⚙",
            "mic": "🎙",
            "attach": "📎",
            "send": "➤",
            "close": "✕",
            "back": "←",
            "new": "＋",
        }
        self.setText(symbols.get(self.icon_name, self.icon_name))
        font = self.font()
        font.setPixelSize(int(self.button_size * 0.45))
        font.setBold(True)
        self.setFont(font)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.surface};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: {self.button_size // 2}px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {theme.surface_alt};
                color: {theme.accent};
                border-color: {theme.accent};
            }}
            QPushButton:checked {{
                background: {theme.accent_soft};
                color: {theme.accent};
                border-color: {theme.accent};
            }}
            QPushButton:pressed {{
                background: {theme.accent};
                color: {theme.background};
            }}
            """
        )
