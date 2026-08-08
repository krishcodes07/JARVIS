"""
Debug Modal Screen — Displays engine diagnostic information (/debug).
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


class DebugModal(ModalScreen[None]):
    """Modal displaying real-time engine diagnostics and component states."""

    DEFAULT_CSS = """
    DebugModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(
        self,
        engine: JarvisEngine | None = None,
        is_generating: bool = False,
        is_voice_active: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.is_generating = is_generating
        self.is_voice_active = is_voice_active
        self.dialog = ModalDialog(
            title="Engine Debug Information",
            dialog_id="debug-dialog",
            width=70,
            height="80%",
            show_search=False,
            footer_text="Esc / Enter close",
            border_style="solid #f97316",
        )

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self.populate_debug()

    def populate_debug(self) -> None:
        self.option_list.clear_options()

        if not self.engine:
            t = Text("  Engine disconnected.", style="bold #ef4444")
            self.option_list.add_option(Option(t, disabled=True))
            return

        c = self.engine.config
        session_id = self.engine.session.session_id if self.engine.session else "N/A"
        tools_cnt = len(self.engine.tool_registry) if self.engine.tool_registry else 0

        info = [
            ("Session ID", session_id, "#60a5fa"),
            ("Active Provider", c.provider.active if c else "N/A", "#3b82f6"),
            ("Active Model", c.provider.model if c else "N/A", "#a78bfa"),
            ("Registered Tools", f"{tools_cnt} tools active", "#22c55e"),
            ("Generating Output", "Yes" if self.is_generating else "No", "#fbbf24" if self.is_generating else "#737373"),
            ("Voice Subsystem", "Listening..." if self.is_voice_active else "Idle / Off", "#ef4444" if self.is_voice_active else "#737373"),
            ("MCP Manager", "Active" if (self.engine.mcp_manager and self.engine.mcp_manager.client.connections) else "Initialized", "#10b981"),
        ]

        header = Text("  Runtime Metrics & Component States\n", style="bold #f97316")
        self.option_list.add_option(Option(header, disabled=True))

        for label, val, color in info:
            t = Text(no_wrap=True)
            t.append(f"  • {label:<22}", style="bold #cbd5e1")
            t.append(val, style=f"bold {color}")
            self.option_list.add_option(Option(t, disabled=True))

        self.option_list.focus()

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_enter(self) -> None:
        self.dismiss(None)
