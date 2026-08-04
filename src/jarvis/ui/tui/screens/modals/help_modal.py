"""
Help Modal Screen — Displays available slash commands and JARVIS keyboard shortcuts.
"""

from __future__ import annotations

from rich.text import Text
from textual.screen import ModalScreen
from textual.widgets import Static

from jarvis.ui.tui.commands import COMMAND_REGISTRY
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog


class HelpModal(ModalScreen[None]):
    """Modal displaying help menu and keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }

    #help-content {
        height: 20;
        margin-top: 1;
        overflow-y: scroll;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.dialog = ModalDialog(
            title="JARVIS Help & Shortcuts",
            dialog_id="help-dialog",
            width=76,
            height=24,
            show_search=False,
            border_style="solid #3b82f6",
        )

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        # Hide the option list since help uses a static content area instead
        self.dialog.option_list.display = False

        # Build help content and mount it inside the dialog
        txt = Text()
        txt.append("Available Slash Commands:\n", style="bold #60a5fa")
        for cmd in COMMAND_REGISTRY:
            txt.append(f"  {cmd.name:<16}", style="bold #f97316")
            txt.append(f" - {cmd.description}\n", style="dim white")

        txt.append("\nKeyboard Shortcuts:\n", style="bold #60a5fa")
        txt.append("  Ctrl+P / /        ", style="bold white")
        txt.append(" - Open Slash Command Palette\n", style="dim white")
        txt.append("  Ctrl+M            ", style="bold white")
        txt.append(" - Open Model Selection Modal\n", style="dim white")
        txt.append("  Ctrl+S            ", style="bold white")
        txt.append(" - Open Sessions Modal\n", style="dim white")
        txt.append("  Alt+V             ", style="bold white")
        txt.append(" - Toggle Hands-Free Voice Mode (STT & TTS)\n", style="dim white")
        txt.append("  Tab               ", style="bold white")
        txt.append(" - Toggle Agent/Mode focus\n", style="dim white")
        txt.append("  Esc               ", style="bold white")
        txt.append(" - Close floating dialogs\n", style="dim white")

        content = Static(txt, id="help-content")
        self.dialog.mount(content)

    def key_escape(self) -> None:
        self.dismiss(None)
