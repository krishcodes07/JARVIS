"""
List Tools Tool — Lists all available built-in and MCP tool names as a comma-separated string.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class ListToolsTool(BaseTool):
    """List all registered built-in tools and connected MCP server tool names."""

    schema = ToolSchema(
        name="list_tools",
        description=(
            "List all available built-in and MCP tool names as a comma-separated string. "
            "Use get_schema(tool_names=[...]) to inspect full parameters schema for any tool."
        ),
        category="basic",
        aliases=["show_tools", "available_tools"],
        keywords=["list", "tools", "mcp", "available"],
        parameters=[],
    )

    async def execute(self, **kwargs: Any) -> str:
        """List built-in and MCP tool names as a comma-separated string."""
        tool_names: set[str] = set()

        # 1. Built-in tools
        if hasattr(self, "config") and self.config:
            from jarvis.tools.registry import ToolRegistry

            registry = ToolRegistry(self.config)
            registry.discover_tools()
            for tool_inst in registry.list_tools():
                tool_names.add(tool_inst.name)

        # 2. MCP server tools
        try:
            from jarvis.mcp.platform.registry import platform_registry

            for tool in platform_registry.tools.values():
                tool_names.add(tool.qualified_name)
        except Exception as e:
            logger.debug("Failed to read MCP platform registry: %s", e)

        if not tool_names:
            return "No tools available."

        return ", ".join(sorted(tool_names))
