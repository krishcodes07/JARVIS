"""
Help Modal Screen — Displays available slash commands and JARVIS keyboard shortcuts.
"""

from __future__ import annotations

from rich.text import Text
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from jarvis.ui.tui.commands import COMMAND_REGISTRY


class HelpModal(ModalScreen[None]):
    """Modal displaying help menu and keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #help-card {
        width: 76;
        height: 80%;
        max-height: 80%;
        background: $surface;
        padding: 1 2;
    }

    #help-card .title-bar {
        height: 1;
        layout: horizontal;
    }

    #help-card .title-text {
        width: 1fr;
        text-style: bold;
        color: #ffffff;
    }

    #help-card .esc-hint {
        width: auto;
        color: #737373;
    }

    #help-scroll {
        height: 1fr;
        margin-top: 1;
        background: transparent;
        scrollbar-size: 0 0;
    }

    #help-scroll Static {
        width: 100%;
    }
    """

    def compose(self):
        with Vertical(id="help-card"):
            from textual.containers import Horizontal
            with Horizontal(classes="title-bar"):
                yield Static("JARVIS Help & Shortcuts", classes="title-text")
                yield Static("esc", classes="esc-hint")
            with VerticalScroll(id="help-scroll"):
                yield Static(self._build_help_text())

    def _build_help_text(self) -> Text:
        """Build the full help content."""
        txt = Text()

        # ── Slash Commands ──
        txt.append("Available Slash Commands:\n", style="bold #60a5fa")
        for cmd in COMMAND_REGISTRY:
            txt.append(f"    {cmd.name:<16}", style="bold #f97316")
            txt.append(f" - {cmd.description}\n", style="dim white")

        # ── Keyboard Shortcuts ──
        txt.append("\nKeyboard Shortcuts:\n", style="bold #60a5fa")

        shortcuts = [
            ("Ctrl+N", "Start a new conversation session"),
            ("Ctrl+P / /", "Open Slash Command Palette"),
            ("Ctrl+M", "Open Model Selection Modal"),
            ("Ctrl+S", "Open Sessions Modal"),
            ("Ctrl+A", "Connect Provider (inside model modal)"),
            ("Alt+V", "Toggle Hands-Free Voice Mode (STT & TTS)"),
            ("Tab", "Insert / for commands or autocomplete"),
            ("Up / Down", "Navigate prompt history"),
            ("Esc", "Cancel generation or close dialogs"),
        ]

        for key, desc in shortcuts:
            txt.append(f"    {key:<20}", style="bold white")
            txt.append(f" - {desc}\n", style="dim white")

        # ── Tips ──
        txt.append("\nTips:\n", style="bold #60a5fa")
        txt.append("    • Click on any ", style="dim white")
        txt.append("user message", style="bold #60a5fa")
        txt.append(" to Revert or Copy it\n", style="dim white")
        txt.append("    • Use ", style="dim white")
        txt.append("/models <provider>", style="bold #f97316")
        txt.append(" to filter models by provider\n", style="dim white")
        txt.append("    • Use ", style="dim white")
        txt.append("/connect", style="bold #f97316")
        txt.append(" to add new API providers\n", style="dim white")

        return txt

    def key_escape(self) -> None:
        self.dismiss(None)
