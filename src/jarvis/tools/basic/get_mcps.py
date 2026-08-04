"""
Get MCPs Tool — List all configured MCP servers and their descriptions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class GetMCPsTool(BaseTool):
    """List all configured MCP servers, status, and descriptions."""

    schema = ToolSchema(
        name="get_mcps",
        description="List all configured MCP (Model Context Protocol) servers, their status (enabled/disabled), transport, and descriptions.",
        category="basic",
        parameters=[],
    )

    async def execute(self, **kwargs: Any) -> str:
        """List all MCP servers."""
        servers_config_file = PROJECT_ROOT / "src" / "jarvis" / "mcp" / "servers.json"

        if hasattr(self, "config") and self.config and self.config.mcp:
            cfg_path = PROJECT_ROOT / self.config.mcp.servers_config
            if cfg_path.exists():
                servers_config_file = cfg_path

        if not servers_config_file.exists():
            return "No MCP servers configuration file found."

        try:
            with open(servers_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            servers = data.get("servers", {})
            if not servers:
                return "No MCP servers configured."

            lines = ["Available MCP Servers:\n"]
            for name, srv in sorted(servers.items()):
                enabled = srv.get("enabled", True)
                status = "Enabled" if enabled else "Disabled"
                desc = srv.get("description", "No description available.")
                transport = srv.get("transport", "stdio")
                lines.append(f"- {name} [{status}] ({transport}): {desc}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error listing MCP servers: {e}"
