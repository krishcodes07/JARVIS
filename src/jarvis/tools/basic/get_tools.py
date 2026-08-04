"""
Get Tools Tool — List all available tools and their descriptions.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class GetToolsTool(BaseTool):
    """List all available tools (built-in and MCP tools) with their descriptions."""

    schema = ToolSchema(
        name="get_tools",
        description="List all available tools (both built-in tools and MCP server tools) along with their categories and descriptions.",
        category="basic",
        parameters=[
            ToolParameter(
                name="filter",
                type="string",
                description="Optional keyword to filter tools by name or description.",
                required=False,
            )
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """List available tools."""
        filter_kw = kwargs.get("filter", "").strip().lower()

        try:
            from jarvis.tools.registry import ToolRegistry

            tools_list: list[tuple[str, str, str]] = []

            # Built-in tools via ToolRegistry
            if hasattr(self, "config") and self.config:
                registry = ToolRegistry(self.config)
                registry.discover_tools()
                for name, tool_inst in registry._tools.items():
                    desc = tool_inst.description
                    cat = tool_inst.category or "built-in"
                    tools_list.append((name, cat, desc))

            # If tools list is empty, discover basic tools manually
            if not tools_list:
                tools_list = [
                    ("run_command", "system", "Execute a terminal shell command."),
                    ("calculator", "basic", "Evaluate mathematical expressions."),
                    ("system_info", "system", "Get system information."),
                    ("process_manager", "system", "Manage running system processes."),
                    ("clipboard", "basic", "Read from or write to the system clipboard."),
                    ("datetime", "basic", "Get current date, time, and timezone information."),
                    ("screenshot", "basic", "Capture a screenshot of the display."),
                    ("url_reader", "basic", "Fetch and extract text content from a web URL."),
                    ("get_mcps", "basic", "List all configured MCP servers and descriptions."),
                    ("get_tools", "basic", "List all available tools and descriptions."),
                ]

            # Filter tools if keyword provided
            if filter_kw:
                tools_list = [
                    (n, c, d)
                    for n, c, d in tools_list
                    if filter_kw in n.lower() or filter_kw in d.lower() or filter_kw in c.lower()
                ]

            if not tools_list:
                return f"No tools found matching filter: '{filter_kw}'"

            lines = [f"Available Tools ({len(tools_list)} total):\n"]
            for name, cat, desc in sorted(tools_list, key=lambda x: x[0]):
                lines.append(f"- {name} [{cat}]: {desc}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error listing tools: {e}"
