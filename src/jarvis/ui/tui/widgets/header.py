"""
Header Widget — Displays styled block ASCII logo for JARVIS.
Hides automatically once the user sends their first message.
"""

from __future__ import annotations

from rich.align import Align
from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget


JARVIS_ASCII_LOGO = r"""
     ▄▄▄   ▄▄▄▄   ▄▄▄▄▄▄▄   ▄▄▄▄  ▄▄▄▄ ▄▄▄▄▄  ▄▄▄▄▄▄▄
     ███ ▄██▀▀██▄ ███▀▀███▄ ▀███  ███▀  ███  █████▀▀▀
     ███ ███  ███ ███▄▄███▀  ███  ███   ███   ▀████▄
▄▄▄  ███ ███▀▀███ ███▀▀██▄   ███▄▄███   ███     ▀████
 ▀████▀  ███  ███ ███  ▀███   ▀████▀   ▄███▄ ███████▀
 
 """


class HeaderWidget(Widget):
    """JARVIS Header displaying ASCII banner. Hides when chat has messages."""

    DEFAULT_CSS = """
    HeaderWidget {
        height: 1fr;
        content-align: center middle;
        align: center middle;
        margin: 0;
        padding: 0;
    }

    HeaderWidget.hidden {
        display: none;
    }
    """

    def render(self) -> RenderResult:
        logo = Text(JARVIS_ASCII_LOGO, style="bold #60a5fa", justify="center")
        sub = Text("\nJust A Rather Very Intelligent System", style="dim #94a3b8", justify="center")
        attr = Text("\nVersion 0.1.0 • AI-Powered Assistant", style="dim #64748b", justify="center")
        combined = Text.assemble(logo, sub, attr, justify="center")
        return Align.center(combined, vertical="middle")

    def show_header(self) -> None:
        self.remove_class("hidden")

    def hide_header(self) -> None:
        self.add_class("hidden")
