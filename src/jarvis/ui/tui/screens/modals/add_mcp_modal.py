"""
Add MCP Server Modal Screen — Interactive dialog to configure and connect a new MCP server.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from jarvis.mcp.creator.tool import add_mcp_server

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class AddMCPModal(ModalScreen[dict[str, Any] | None]):
    """Modal dialog for adding and connecting a new MCP server."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    DEFAULT_CSS = """
    AddMCPModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.65);
    }

    #add-mcp-card {
        width: 66;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: none;
        padding: 1 2;
    }

    #add-mcp-header-row {
        layout: horizontal;
        height: 1;
        margin-bottom: 1;
    }

    #add-mcp-title {
        width: 1fr;
        color: #ffffff;
        text-style: bold;
    }

    #add-mcp-esc {
        width: auto;
        color: #737373;
        text-style: dim;
    }

    .field-row {
        height: auto;
        margin-bottom: 1;
    }

    .field-label {
        color: #94a3b8;
        text-style: bold;
        margin-bottom: 0;
    }

    .field-input {
        width: 1fr;
        height: 1;
        background: #1e293b;
        color: #ffffff;
        border: none !important;
        padding: 0 1;
    }

    .field-input:focus {
        background: #334155;
        color: #ffffff;
        border: none !important;
    }

    #add-mcp-status {
        height: 1;
        margin-top: 1;
        color: #f59e0b;
    }

    #add-mcp-actions {
        layout: horizontal;
        align: right middle;
        height: 3;
        margin-top: 1;
    }

    #btn-cancel {
        margin-right: 2;
        background: #262626;
        color: #d4d4d4;
        border: none;
    }

    #btn-submit {
        background: #3b82f6;
        color: #ffffff;
        text-style: bold;
        border: none;
    }

    #btn-submit:hover {
        background: #2563eb;
    }
    """

    def __init__(
        self,
        engine: JarvisEngine | None = None,
        initial_name: str = "",
        initial_command: str = "npx",
        initial_args: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self._initial_name = initial_name
        self._initial_command = initial_command
        self._initial_args = initial_args

        self.name_input = Input(
            value=self._initial_name,
            placeholder="e.g. github, postgres",
            id="input-name",
            classes="field-input",
        )
        self.command_input = Input(
            value=self._initial_command,
            placeholder="e.g. npx, uvx, python",
            id="input-command",
            classes="field-input",
        )
        self.args_input = Input(
            value=self._initial_args,
            placeholder="e.g. -y @mcp/server-github",
            id="input-args",
            classes="field-input",
        )
        self.transport_input = Input(
            value="stdio",
            placeholder="stdio, sse, http",
            id="input-transport",
            classes="field-input",
        )
        self.env_input = Input(
            placeholder="e.g. GITHUB_TOKEN=xxx",
            id="input-env",
            classes="field-input",
        )
        self.status_label = Static("", id="add-mcp-status")

    def compose(self):
        with Vertical(id="add-mcp-card"):
            with Horizontal(id="add-mcp-header-row"):
                yield Static("+ Connect New MCP Server", id="add-mcp-title")
                yield Static("Esc Cancel", id="add-mcp-esc")

            with Vertical(classes="field-row"):
                yield Label("Server Name *", classes="field-label")
                yield self.name_input

            with Vertical(classes="field-row"):
                yield Label("Command *", classes="field-label")
                yield self.command_input

            with Vertical(classes="field-row"):
                yield Label("Arguments", classes="field-label")
                yield self.args_input

            with Vertical(classes="field-row"):
                yield Label("Transport", classes="field-label")
                yield self.transport_input

            with Vertical(classes="field-row"):
                yield Label("Environment Variables (optional)", classes="field-label")
                yield self.env_input

            yield self.status_label

            with Horizontal(id="add-mcp-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Connect & Save", id="btn-submit", variant="primary")

    def on_mount(self) -> None:
        self.name_input.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-submit":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _parse_env_vars(self, raw: str) -> dict[str, str]:
        """Parse key=val strings into a dictionary."""
        result: dict[str, str] = {}
        if not raw.strip():
            return result

        # Split on commas or spaces while respecting quotes
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip().strip("'\"")
        return result

    @work(exclusive=True)
    async def _submit(self) -> None:
        name = self.name_input.value.strip()
        command = self.command_input.value.strip() or "npx"
        raw_args = self.args_input.value.strip()
        transport = self.transport_input.value.strip() or "stdio"
        env_dict = self._parse_env_vars(self.env_input.value)

        if not name:
            self.status_label.update("[red]⚠ Server name is required.[/red]")
            self.name_input.focus()
            return

        # Parse args using shlex
        args: list[str] = []
        if raw_args:
            try:
                args = shlex.split(raw_args, posix=False)
            except Exception:
                args = raw_args.split()

        self.status_label.update(f"[cyan]Connecting to MCP server '{name}'...[/cyan]")

        try:
            res = await add_mcp_server(
                name=name,
                command=command,
                args=args,
                transport=transport,
                env=env_dict,
                auto_connect=True,
                engine=self.engine,
            )

            if res.get("connected") or res.get("success"):
                tools_cnt = res.get("tools_count", 0)
                self.status_label.update(f"[green]✓ Connected! ({tools_cnt} tools)[/green]")
                await asyncio.sleep(0.6)
                self.dismiss(res)
            else:
                msg = res.get("message", "Connection failed")
                self.status_label.update(f"[red]⚠ {msg}[/red]")
        except Exception as e:
            logger.error("Error adding MCP server: %s", e, exc_info=True)
            self.status_label.update(f"[red]⚠ Error: {e}[/red]")
