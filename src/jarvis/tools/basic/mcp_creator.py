"""
MCP Creator Tool — Allows JARVIS to dynamically add, configure, and connect new MCP servers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from jarvis.mcp.creator.tool import add_mcp_server
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class MCPCreatorTool(BaseTool):
    """Tool for registering, installing, and connecting new MCP servers into JARVIS."""

    schema = ToolSchema(
        name="mcp_creator",
        description=(
            "Add, configure, and connect a new Model Context Protocol (MCP) server to JARVIS. "
            "Persists the configuration in ~/.jarvis/mcp/servers.json and connects immediately. "
            "Use this tool after finding MCP server details via web search (npx, uvx, etc.)."
        ),
        category="basic",
        aliases=["add_mcp", "install_mcp", "create_mcp_server", "register_mcp"],
        keywords=["mcp", "server", "install", "add", "tool", "integration", "npx", "uvx"],
        parameters=[
            ToolParameter(
                name="name",
                type="string",
                description="Identifier name for the MCP server (e.g., 'github', 'postgres').",
                required=True,
            ),
            ToolParameter(
                name="command",
                type="string",
                description="Executable command (e.g. 'npx', 'uvx', 'python', 'node', 'docker').",
                required=True,
            ),
            ToolParameter(
                name="args",
                type="array",
                description="List of command line arguments (e.g. ['-y', '@mcp/server-pkg']).",
                required=False,
                default=[],
            ),
            ToolParameter(
                name="transport",
                type="string",
                description="Transport: 'stdio', 'sse', or 'streamable_http'. Default: 'stdio'.",
                required=False,
                default="stdio",
                enum=["stdio", "sse", "streamable_http"],
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Description of what this MCP server and its tools do.",
                required=False,
                default="",
            ),
            ToolParameter(
                name="env",
                type="object",
                description="Optional dictionary of environment variables or API keys.",
                required=False,
                default={},
            ),
            ToolParameter(
                name="url",
                type="string",
                description="Optional endpoint URL if connecting to a remote SSE or HTTP server.",
                required=False,
                default="",
            ),
            ToolParameter(
                name="auto_connect",
                type="boolean",
                description="Whether to immediately test-connect the added server (default: True).",
                required=False,
                default=True,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute MCP server creation and registration."""
        name = kwargs.get("name")
        if not name:
            return "❌ Error: Parameter 'name' is required."

        command = kwargs.get("command")
        if not command:
            return "❌ Error: Parameter 'command' is required."

        args = kwargs.get("args") or []
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = args.split()

        transport = kwargs.get("transport", "stdio")
        description = kwargs.get("description", "")
        env = kwargs.get("env") or {}
        if isinstance(env, str):
            try:
                env = json.loads(env)
            except Exception:
                env = {}

        url = kwargs.get("url")
        auto_connect = kwargs.get("auto_connect", True)
        if isinstance(auto_connect, str):
            auto_connect = auto_connect.lower() in ("true", "1", "yes")

        engine = getattr(self, "engine", None)
        if not engine:
            cfg = getattr(self, "config", None)
            engine = getattr(cfg, "_engine", None)
        if not engine:
            try:
                from jarvis.core.engine import get_active_engine
                engine = get_active_engine()
            except Exception:
                engine = None

        try:
            res = await add_mcp_server(
                name=name,
                command=command,
                args=args,
                transport=transport,
                description=description,
                env=env,
                url=url,
                auto_connect=auto_connect,
                engine=engine,
            )

            status_icon = "✅" if res.get("connected") or res.get("success") else "⚠️"
            is_conn = res.get("connected")
            status_text = "Connected" if is_conn else "Saved (Ready to connect)"
            output_lines = [
                f"{status_icon} **MCP Server Registered**: `{res.get('name')}`",
                f"- **Command**: `{command}` {' '.join(args)}",
                f"- **Transport**: `{transport}`",
                "- **Config Saved To**: `~/.jarvis/mcp/servers.json`",
                f"- **Status**: {status_text}",
                f"- **Tools Discovered**: {res.get('tools_count', 0)}",
                f"\n{res.get('message', '')}",
            ]
            return "\n".join(output_lines)

        except Exception as e:
            logger.error("Failed to add MCP server '%s': %s", name, e, exc_info=True)
            return f"❌ Failed to add MCP server '{name}': {e}"
