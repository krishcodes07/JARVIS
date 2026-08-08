"""
MCP Server Status Modal Screen — View and toggle MCP servers (/mcp).
Displays server name, connection status, tool/resource/prompt counts.
Click on a server to enable/disable it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual import work
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.utils import handle_search_key_navigation
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class MCPModal(ModalScreen[None]):
    """Modal dialog for viewing and toggling MCP server connections."""

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
            width=72,
            height="80%",
            show_search=True,
            search_placeholder="Search servers...",
            footer_text="Enter toggle   ↑↓ navigate   Esc close",
        )
        self.servers_data: list[dict[str, Any]] = []
        self._is_loading: bool = True
        self._loading_timer = None
        self._loading_frame: int = 0

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
        self._loading_timer = self.set_interval(0.3, self._animate_loading)
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
            import asyncio
            await asyncio.sleep(0.15)
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to the option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def _refresh_servers_data(self) -> None:
        """Build a unified list of all servers with their live status."""
        if not self.engine or not self.engine.mcp_manager:
            self.servers_data = []
            return

        mgr = self.engine.mcp_manager
        connections = mgr.client.connections

        # Get all discovered servers (includes enabled field from config)
        available = mgr.get_available_servers()

        merged: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        # First: servers with active connections (connected or errored)
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
            })
            seen_names.add(name)

        # Then: discovered but not currently connected servers
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
                "status": "disabled",
                "connected": False,
            })

        # Sort: connected first, then alphabetically
        merged.sort(key=lambda s: (0 if s["connected"] else 1, s["name"].lower()))
        self.servers_data = merged

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(filter_text=event.value)

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()

        if self._is_loading:
            dots = "." * ((self._loading_frame % 3) + 1)
            for _ in range(4):
                self.option_list.add_option(Option(Text(""), disabled=True))
            msg = f"Fetching MCP servers {dots:<3}"
            t = Text(msg.center(64), style="bold #22c55e")
            self.option_list.add_option(Option(t, disabled=True))
            return

        query = filter_text.strip().lower()

        connected = [s for s in self.servers_data if s["connected"]]
        not_connected = [s for s in self.servers_data if not s["connected"]]

        has_content = False

        # Connected servers
        filtered_connected = self._filter_servers(connected, query)
        if filtered_connected:
            has_content = True
            header = Text()
            header.append(f"  Connected ({len(filtered_connected)})", style="bold #22c55e")
            self.option_list.add_option(Option(header, disabled=True))

            for server in filtered_connected:
                self.option_list.add_option(
                    Option(
                        self._build_server_option(server, is_connected=True),
                        id=f"mcp::{server['name']}",
                    )
                )

        # Not connected / disabled servers
        filtered_not_connected = self._filter_servers(not_connected, query)
        if filtered_not_connected:
            has_content = True
            header = Text()
            header.append(f"  Disabled ({len(filtered_not_connected)})", style="bold #737373")
            self.option_list.add_option(Option(header, disabled=True))

            for server in filtered_not_connected:
                self.option_list.add_option(
                    Option(
                        self._build_server_option(server, is_connected=False),
                        id=f"mcp::{server['name']}",
                    )
                )

        if not has_content:
            empty = Text()
            if query:
                empty.append("  No servers matching filter", style="dim #737373")
            else:
                empty.append("  No MCP servers configured", style="dim #737373")
            self.option_list.add_option(Option(empty, disabled=True))

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
            t.append("  ○ ", style="bold #555555")

        # Server name
        t.append(f"{server['name']:<20}", style="bold #ffffff" if is_connected else "bold #737373")

        # Stats or status
        if is_connected:
            tools = server.get("tools_count", 0)
            resources = server.get("resources_count", 0)
            prompts = server.get("prompts_count", 0)
            t.append(f" {tools} tools", style="#60a5fa")
            t.append(f"  {resources} res", style="#a78bfa")
            t.append(f"  {prompts} prompts", style="#f59e0b")
        else:
            status = server.get("status", "disabled")
            if status.startswith("error"):
                t.append(f" {status}", style="dim #ef4444")
            else:
                t.append(" disabled", style="dim #555555")

        # Version
        version = server.get("version", "")
        if version:
            t.append(f"  v{version}", style="dim #737373")

        return t

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Toggle server connection on click/Enter."""
        option_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if not option_id or not option_id.startswith("mcp::"):
            return
        server_name = option_id.removeprefix("mcp::")
        self._toggle_server(server_name)

    @work(exclusive=True)
    async def _toggle_server(self, server_name: str) -> None:
        """Enable or disable an MCP server by connecting/disconnecting."""
        if not self.engine or not self.engine.mcp_manager:
            return

        self._is_loading = True
        self._loading_frame = 0
        if not self._loading_timer:
            self._loading_timer = self.set_interval(0.3, self._animate_loading)
        if self.is_mounted:
            self.populate_list(self.search_input.value if self.search_input else "")

        mgr = self.engine.mcp_manager
        conn = mgr.client.connections.get(server_name)

        try:
            if conn and conn.connected:
                # Disconnect (disable)
                try:
                    await mgr.client.disconnect(server_name)
                    logger.info("MCP server '%s' disabled via modal.", server_name)
                    toast_fn = getattr(self.app.screen, "show_toast", None)
                    if toast_fn:
                        toast_fn(f"MCP server '{server_name}' disabled", title="MCP Server", style="info")
                except Exception as e:
                    logger.warning("Failed to disconnect MCP server '%s': %s", server_name, e)
                    toast_fn = getattr(self.app.screen, "show_toast", None)
                    if toast_fn:
                        toast_fn(f"Failed to disconnect '{server_name}': {e}", title="MCP Error", style="error")
            else:
                # Reconnect (enable)
                target_config = mgr.get_server_config(server_name, force_enabled=True)
                if target_config:
                    try:
                        await mgr.client.connect(target_config)
                        logger.info("MCP server '%s' enabled via modal.", server_name)
                        toast_fn = getattr(self.app.screen, "show_toast", None)
                        if toast_fn:
                            toast_fn(f"MCP server '{server_name}' enabled", title="MCP Server", style="success")
                    except Exception as e:
                        logger.warning("Failed to connect MCP server '%s': %s", server_name, e)
                        toast_fn = getattr(self.app.screen, "show_toast", None)
                        if toast_fn:
                            toast_fn(f"Failed to connect '{server_name}': {e}", title="MCP Error", style="error")

            # Refresh the list
            self._refresh_servers_data()
        finally:
            self._is_loading = False
            if self._loading_timer:
                self._loading_timer.stop()
                self._loading_timer = None
            if self.is_mounted:
                self.populate_list(self.search_input.value if self.search_input else "")

    def key_escape(self) -> None:
        self.dismiss(None)
