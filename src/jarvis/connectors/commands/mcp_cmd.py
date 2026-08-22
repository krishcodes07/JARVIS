"""
MCP Command — Inspect, connect, and disconnect Model Context Protocol servers (/mcp).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jarvis.connectors.commands.models import BaseCommand, CommandContext
from jarvis.mcp.platform.registry import platform_registry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MCPCommand(BaseCommand):
    """Command to view, connect, and disconnect MCP servers and tools."""

    name: str = "mcp"
    aliases: list[str] = ["mcps"]
    description: str = "View, connect, and inspect MCP servers and tools."
    usage: str = "/mcp [status | list | connect <server> | disconnect <server> | <server_name>]"
    category: str = "MCP"

    async def execute(self, ctx: CommandContext) -> str:
        """Handle /mcp command execution."""
        mcp_mgr = ctx.engine.mcp_manager
        config = ctx.engine.config

        if not config or not config.mcp.enabled or not mcp_mgr:
            return (
                "🔌 **MCP Subsystem Status**: `Disabled`\n\n"
                "To enable MCP, set `mcp.enabled: true` in your `jarvis.yaml`."
            )

        args = ctx.args
        if hasattr(mcp_mgr, "get_available_servers"):
            available_servers = mcp_mgr.get_available_servers()
        elif hasattr(mcp_mgr, "list_available_servers"):
            available_servers = mcp_mgr.list_available_servers()
        else:
            available_servers = []

        active_connections = getattr(mcp_mgr, "servers", {})

        # 1. No args or 'status' / 'list' -> List all MCP servers (built-in + servers.json + config)
        if not args or args[0].lower() in ("status", "list", "ls"):
            if not available_servers:
                return (
                    "🔌 **MCP Subsystem**: `Enabled`\n\n"
                    "No MCP servers currently discovered or configured in `servers.json`."
                )

            lines = ["🔌 **MCP Servers & Status**:\n"]

            for sinfo in available_servers:
                sname = sinfo["name"]
                is_conn = sname in active_connections
                marker = "🟢 **Connected**" if is_conn else "⚪ **Disconnected**"

                desc = sinfo.get("description") or "MCP Server"
                manifest = getattr(mcp_mgr, "_manifests", {}).get(sname)
                category = getattr(manifest, "category", "general") if manifest else "external"

                # Find tools registered for this server in platform_registry
                tools = platform_registry.find_tools(server=sname)
                if not tools:
                    tools = [
                        t for t in platform_registry.tools.values()
                        if t.server_name.lower() == sname.lower()
                        or t.qualified_name.lower().startswith(f"{sname.lower()}__")
                        or t.qualified_name.lower().startswith(f"{sname.lower()}_")
                    ]

                lines.append(
                    f"• `{sname}` — {marker}\n"
                    f"   Category: `{category}` | Tools: **{len(tools)}**\n"
                    f"   *{desc}*\n"
                )

            lines.append(
                "────────────────\n"
                "💡 **Commands**:\n"
                "• View server tools: `/mcp <server_name>`\n"
                "• Connect server: `/mcp connect <server_name>`\n"
                "• Disconnect server: `/mcp disconnect <server_name>`"
            )
            return "\n".join(lines)

        subcmd = args[0].lower()

        # 2. Subcommand: connect / enable / start
        if subcmd in ("connect", "enable", "start"):
            if len(args) < 2:
                return "⚠️ **Usage**: `/mcp connect <server_name>`"

            target_server = args[1].lower()
            if hasattr(mcp_mgr, "connect_server"):
                ok, msg = await mcp_mgr.connect_server(target_server)
                if ok:
                    return f"✅ **MCP Server Connected**\n\n{msg}"
                return f"⚠️ **Connection Failed**\n\n{msg}"
            return "⚠️ Dynamic MCP connection is not supported by current MCP manager."

        # 3. Subcommand: disconnect / disable / stop
        if subcmd in ("disconnect", "disable", "stop"):
            if len(args) < 2:
                return "⚠️ **Usage**: `/mcp disconnect <server_name>`"

            target_server = args[1].lower()
            if hasattr(mcp_mgr, "disconnect_server"):
                ok, msg = await mcp_mgr.disconnect_server(target_server)
                if ok:
                    return f"🔌 **MCP Server Disconnected**\n\n{msg}"
                return f"⚠️ **Disconnection Failed**\n\n{msg}"
            return "⚠️ Dynamic MCP disconnection is not supported by current MCP manager."

        # 4. Server details -> /mcp <server_name> or /mcp tools <server_name>
        target_server = args[1].lower() if subcmd == "tools" and len(args) > 1 else subcmd
        matching_info = next((s for s in available_servers if s["name"].lower() == target_server), None)

        is_conn = target_server in active_connections
        status_text = "🟢 Connected" if is_conn else "⚪ Disconnected"

        # Gather tools for this server from platform_registry
        server_tools = platform_registry.find_tools(server=target_server)
        if not server_tools:
            server_tools = [
                t for t in platform_registry.tools.values()
                if t.server_name.lower() == target_server
                or t.qualified_name.lower().startswith(f"{target_server}__")
                or t.qualified_name.lower().startswith(f"{target_server}_")
            ]

        # Gather resources for this server from platform_registry
        server_resources = platform_registry.find_resources(server=target_server)

        desc = matching_info.get("description") if matching_info else "MCP Server"

        lines = [
            f"🔌 **MCP Server**: `{target_server}`\n"
            f"• **Status:** {status_text}\n"
            f"• **Description:** {desc}\n"
            f"• **Available Tools:** {len(server_tools)}\n"
        ]

        if server_resources:
            lines.append(f"• **Available Resources:** {len(server_resources)}\n")

        lines.append("🔧 **Exposed Tools**:\n")

        if server_tools:
            for tool in sorted(server_tools, key=lambda t: t.name):
                lines.append(f"• `/{tool.name}` — {tool.description or 'No description'}")
        else:
            if is_conn:
                lines.append("*(No exposed tools reported by this server)*")
            else:
                lines.append(
                    "*(Server is currently disconnected)*\n\n"
                    f"💡 *To connect this server:* `/mcp connect {target_server}`"
                )

        return "\n".join(lines)
