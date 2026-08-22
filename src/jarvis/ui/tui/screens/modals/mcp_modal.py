"""
MCP Server Status Modal Screen — View, authenticate, and toggle MCP servers (/mcp).

Displays server name, connection status, tool/resource/prompt counts.
Selecting an unauthenticated OAuth service (like Gmail) opens the system browser
for seamless 1-click authentication and persists the connection across restarts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from rich.text import Text
from textual import work
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.screens.modals.add_mcp_modal import AddMCPModal
from jarvis.ui.tui.utils import handle_search_key_navigation
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class MCPModal(ModalScreen[None]):
    """Modal dialog for viewing, authenticating, and toggling MCP server connections."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+a", "add_mcp", "Add MCP", priority=True),
        Binding("a", "add_mcp", "Add MCP", show=False),
    ]

    DEFAULT_CSS = """
    MCPModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.dialog = ModalDialog(
            title="MCP Servers",
            dialog_id="mcp-dialog",
            width=76,
            height="82%",
            show_search=True,
            search_placeholder="Search servers... (Ctrl+A to Add)",
            footer_text="Enter toggle/connect   Ctrl+A Add MCP   ↑↓ navigate   Esc close",
        )
        self.servers_data: list[dict[str, Any]] = []
        self._is_loading: bool = True
        self._loading_timer = None
        self._loading_frame: int = 0
        self._status_message: str = ""

    def action_add_mcp(self) -> None:
        """Open the Add MCP Server modal dialog."""
        self.app.push_screen(AddMCPModal(self.engine), callback=self._on_add_mcp_closed)

    def _on_add_mcp_closed(self, result: dict[str, Any] | None) -> None:
        """Callback when AddMCPModal closes."""
        if result and (result.get("connected") or result.get("success")):
            toast_fn = self._get_toast_fn()
            if toast_fn:
                name = result.get("name", "server")
                tools = result.get("tools_count", 0)
                toast_fn(
                    f"Connected to '{name}' ({tools} tools)",
                    title="MCP Connected",
                    style="success",
                )
            self.load_mcp_servers_async()

    @property
    def search_input(self) -> Input | None:
        return self.dialog.search_input

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        if self.search_input:
            self.search_input.focus()
        self._is_loading = True
        self._loading_frame = 0
        self._loading_timer = self.set_interval(0.2, self._animate_loading)
        self.populate_list()
        self.load_mcp_servers_async()

    def _animate_loading(self) -> None:
        if self._is_loading and self.is_mounted:
            self._loading_frame += 1
            self.populate_list(self.search_input.value if self.search_input else "")

    def on_unmount(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    @work(exclusive=True)
    async def load_mcp_servers_async(self) -> None:
        try:
            self._refresh_servers_data()
            await asyncio.sleep(0.1)
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to the option list."""
        if event.key in ("ctrl+a",):
            self.action_add_mcp()
            event.stop()
            return
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def _refresh_servers_data(self) -> None:
        """Build a unified list of all servers with their live status."""
        if not self.engine or not self.engine.mcp_manager:
            self.servers_data = []
            return

        mgr = self.engine.mcp_manager
        connections = mgr.client.connections

        # Get all discoverable and registry configured servers
        available = mgr.get_available_servers()

        merged: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        # 1. Servers with active live connections
        for name, conn in connections.items():
            from jarvis.mcp.platform.registry import platform_registry
            manifest = platform_registry.servers.get(name)
            merged.append({
                "name": conn.name,
                "version": manifest.version if manifest else "1.0.0",
                "description": (
                    conn.config.description
                    or (manifest.description if manifest else "")
                ),
                "tools_count": len(conn.tools),
                "resources_count": len(conn.resources),
                "prompts_count": len(conn.prompts),
                "status": "connected" if conn.connected else f"error: {conn.error or 'failed'}",
                "connected": conn.connected,
                "needs_oauth": False,
            })
            seen_names.add(name)

        # 2. Available catalog servers not currently connected
        for srv in available:
            name = srv.get("name", "")
            if name in seen_names:
                continue

            merged.append({
                "name": name,
                "version": srv.get("version", "1.0.0"),
                "description": srv.get("description", ""),
                "tools_count": 0,
                "resources_count": 0,
                "prompts_count": 0,
                "status": "disconnected",
                "connected": False,
            })

        # Sort: connected first, then alphabetically
        merged.sort(key=lambda s: (0 if s["connected"] else 1, s["name"].lower()))
        self.servers_data = merged

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(filter_text=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Toggle selected server on Enter in search box."""
        if self.option_list.highlighted is not None:
            self.option_list.action_select()

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()

        if self._is_loading:
            dots = "." * ((self._loading_frame % 3) + 1)
            for _ in range(4):
                self.option_list.add_option(Option(Text(""), disabled=True))
            msg = self._status_message or f"Loading MCP servers {dots:<3}"
            t = Text(msg.center(68), style="bold #38bdf8")
            self.option_list.add_option(Option(t, disabled=True))
            return

        query = filter_text.strip().lower()

        # Always add the "+ Connect New MCP Server" action at the top
        add_text = Text()
        add_text.append("  ✚  ", style="bold #38bdf8")
        add_text.append("Connect New MCP Server", style="bold #38bdf8")
        add_text.append("  (Ctrl+A / npx, uvx, python, SSE, HTTP)", style="dim #94a3b8")
        self.option_list.add_option(Option(add_text, id="mcp_add_action"))

        connected = [s for s in self.servers_data if s["connected"]]
        not_connected = [s for s in self.servers_data if not s["connected"]]

        first_selectable_idx: int | None = 0
        option_idx = 1

        # Connected servers section
        filtered_connected = self._filter_servers(connected, query)
        if filtered_connected:
            header = Text()
            header.append(
                f"\n  ● Active Connections ({len(filtered_connected)})",
                style="bold #22c55e",
            )
            self.option_list.add_option(Option(header, disabled=True))
            option_idx += 1

            for server in filtered_connected:
                self.option_list.add_option(
                    Option(
                        self._build_server_option(server, is_connected=True),
                        id=f"mcp::{server['name']}",
                    )
                )
                option_idx += 1

        # Available / Disconnected servers section
        filtered_not_connected = self._filter_servers(not_connected, query)
        if filtered_not_connected:
            header = Text()
            header.append(
                f"\n  ○ Configured Integrations ({len(filtered_not_connected)})",
                style="bold #94a3b8",
            )
            self.option_list.add_option(Option(header, disabled=True))
            option_idx += 1

            for server in filtered_not_connected:
                self.option_list.add_option(
                    Option(
                        self._build_server_option(server, is_connected=False),
                        id=f"mcp::{server['name']}",
                    )
                )
                option_idx += 1

        if not filtered_connected and not filtered_not_connected:
            self.option_list.add_option(Option(Text(""), disabled=True))
            empty = Text()
            if query:
                empty.append(f"  No configured servers matching '{query}'", style="dim #737373")
            else:
                empty.append("  No MCP servers configured.", style="dim #737373")
                empty.append(
                    "\n  Press [Ctrl+A] or select '+' above to connect an MCP integration.",
                    style="italic #64748b",
                )
            self.option_list.add_option(Option(empty, disabled=True))

        # Highlight "+ Connect New MCP Server" by default if list is empty, or first item
        if first_selectable_idx is not None:
            self.option_list.highlighted = first_selectable_idx

    def _filter_servers(self, servers: list[dict], query: str) -> list[dict]:
        if not query:
            return servers
        return [
            s for s in servers
            if query in s["name"].lower()
            or query in s.get("description", "").lower()
        ]

    def _build_server_option(self, server: dict, is_connected: bool) -> Text:
        t = Text()
        if is_connected:
            t.append("  ● ", style="bold #22c55e")
        else:
            t.append("  ○ ", style="bold #64748b")

        # Server name
        t.append(f"{server['name']:<18}", style="bold #ffffff" if is_connected else "bold #cbd5e1")

        # Stats or status
        if is_connected:
            tools = server.get("tools_count", 0)
            resources = server.get("resources_count", 0)
            prompts = server.get("prompts_count", 0)
            t.append(f" {tools} tools", style="#38bdf8")
            t.append(f"  {resources} res", style="#a78bfa")
            t.append(f"  {prompts} prompts", style="#f59e0b")
        else:
            status = server.get("status", "disconnected")
            if status.startswith("error"):
                t.append(f" {status}", style="dim #ef4444")
            else:
                t.append(" disconnected", style="dim #64748b")

        return t

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Toggle server connection or trigger OAuth on selection."""
        option_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if not option_id:
            return

        if option_id == "mcp_add_action":
            self.action_add_mcp()
            return

        if not option_id.startswith("mcp::"):
            return
        server_name = option_id.removeprefix("mcp::")
        self._toggle_server(server_name)

    def _get_toast_fn(self):
        """Resolve the toast function from the underlying main screen."""
        # Walk the screen stack to find the main screen with show_toast
        for screen in reversed(self.app.screen_stack):
            fn = getattr(screen, "show_toast", None)
            if fn is not None:
                return fn
        return None

    @work(exclusive=True)
    async def _toggle_server(self, server_name: str) -> None:
        """Connect with browser OAuth if required, or toggle existing connection."""
        if not self.engine or not self.engine.mcp_manager:
            return

        mgr = self.engine.mcp_manager
        conn = mgr.client.connections.get(server_name)
        toast_fn = self._get_toast_fn()

        self._is_loading = True
        self._loading_frame = 0
        if not self._loading_timer:
            self._loading_timer = self.set_interval(0.2, self._animate_loading)

        try:
            if conn and conn.connected:
                # ── Disconnect server ──
                self._status_message = f"Disconnecting '{server_name}'..."
                if self.is_mounted:
                    self.populate_list(self.search_input.value if self.search_input else "")

                ok, msg = await mgr.disconnect_server(server_name)
                if ok:
                    logger.info("MCP server '%s' disconnected.", server_name)
                    if toast_fn:
                        toast_fn(
                            f"Disconnected from '{server_name}'",
                            title="MCP Server",
                            style="info",
                        )
                else:
                    logger.warning("Failed to disconnect '%s': %s", server_name, msg)
                    if toast_fn:
                        toast_fn(msg, title="MCP Error", style="error")

            else:
                # ── Connect server ──
                self._status_message = f"Connecting '{server_name}'..."
                if self.is_mounted:
                    self.populate_list(self.search_input.value if self.search_input else "")

                ok, msg = await mgr.connect_server(server_name)
                if ok:
                    logger.info("MCP server '%s' connected successfully.", server_name)
                    if toast_fn:
                        toast_fn(
                            f"Connected to '{server_name}'",
                            title="MCP Server",
                            style="success",
                        )
                else:
                    logger.warning("Failed to connect '%s': %s", server_name, msg)
                    if toast_fn:
                        toast_fn(msg, title="MCP Error", style="error")

            # Refresh data
            self._refresh_servers_data()
        finally:
            self._status_message = ""
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def key_escape(self) -> None:
        self.dismiss(None)
