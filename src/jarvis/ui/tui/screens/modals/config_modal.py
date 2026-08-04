"""
Config Modal Screen — Interactive dialog displaying active JARVIS settings (/config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from rich.text import Text
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine


class ConfigModal(ModalScreen[None]):
    """Modal displaying formatted configuration status."""

    DEFAULT_CSS = """
    ConfigModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="JARVIS Configuration",
            dialog_id="config-dialog",
            width=68,
            height=20,
            show_search=False,
            footer_text="Esc / Enter close",
            border_style="solid #3b82f6",
        )

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self.populate_config()

    def populate_config(self) -> None:
        self.option_list.clear_options()

        if not self.engine or not self.engine.config:
            t = Text("  No active engine configuration found.", style="dim #ef4444")
            self.option_list.add_option(Option(t, disabled=True))
            return

        c = self.engine.config

        items = [
            ("LLM Provider", c.provider.active.upper(), "#3b82f6"),
            ("Active Model", c.provider.model, "#60a5fa"),
            ("Temperature", str(c.provider.temperature), "#a78bfa"),
            ("Memory System", "Enabled" if getattr(c.memory.conversation, "enabled", False) else "Disabled", "#22c55e" if getattr(c.memory.conversation, "enabled", False) else "#737373"),
            ("Tools System", "Enabled" if getattr(c.tools, "enabled", False) else "Disabled", "#22c55e" if getattr(c.tools, "enabled", False) else "#737373"),
            ("MCP Integration", "Enabled" if getattr(c.mcp, "enabled", False) else "Disabled", "#22c55e" if getattr(c.mcp, "enabled", False) else "#737373"),
        ]

        header = Text("  System & Subsystem Status\n", style="bold #ffffff")
        self.option_list.add_option(Option(header, disabled=True))

        for label, val, color in items:
            t = Text(no_wrap=True)
            t.append(f"  • {label:<22}", style="bold #cbd5e1")
            t.append(val, style=f"bold {color}")
            self.option_list.add_option(Option(t, disabled=True))

        self.option_list.focus()

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_enter(self) -> None:
        self.dismiss(None)
