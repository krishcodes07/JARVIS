"""Dynamic QSS stylesheet generator for GUI themes."""

from __future__ import annotations

from jarvis.ui.gui.themes.tokens import Theme


def build_stylesheet(theme: Theme) -> str:
    """Return global QSS stylesheet formatted for active Theme tokens."""

    return f"""
        QWidget {{
            color: {theme.text};
            font-family: "Segoe UI", system-ui, sans-serif;
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
        QFrame#PromptCard {{
            background: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 32px;
        }}
        QLineEdit#PromptInput {{
            background: transparent;
            color: {theme.text};
            border: none;
            padding: 0 8px;
            font-size: 14px;
        }}
        QListWidget#SessionList {{
            background: transparent;
            border: none;
            outline: none;
        }}
        QListWidget#SessionList::item {{
            background: {theme.surface_alt};
            color: {theme.text};
            border-radius: 6px;
            padding: 8px 10px;
            margin-bottom: 4px;
        }}
        QListWidget#SessionList::item:hover {{
            background: {theme.accent_soft};
            color: {theme.accent};
        }}
        QListWidget#SessionList::item:selected {{
            background: {theme.accent};
            color: {theme.background};
            font-weight: bold;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.border};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """
