"""
Get Schema Tool — Inspect and retrieve JSON parameter schemas for specific tools by name.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class GetSchemaTool(BaseTool):
    """Retrieve detailed parameter schemas for requested tool names."""

    schema = ToolSchema(
        name="get_schema",
        description=(
            "Retrieve parameter JSON schemas for one or more specified tools by tool name. "
            "Pass tool names as a list (e.g. ['read_file', 'telegram__send_message'])."
        ),
        category="basic",
        aliases=["tool_schema", "inspect_tool"],
        keywords=["schema", "tool", "parameters", "inspect"],
        parameters=[
            ToolParameter(
                name="tool_names",
                type="array",
                description="List of tool names (or comma-separated string of tool names) to retrieve schemas for.",
                required=True,
            )
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Fetch schemas for the specified tool names."""
        raw_names = kwargs.get("tool_names") or kwargs.get("names") or []
        if isinstance(raw_names, str):
            names = [n.strip() for n in raw_names.split(",") if n.strip()]
        elif isinstance(raw_names, list):
            names = [str(n).strip() for n in raw_names if str(n).strip()]
        else:
            return "Please provide a non-empty list of tool names in `tool_names`."

        if not names:
            return "Please provide at least one tool name."

        found_schemas: dict[str, Any] = {}
        missing_names: list[str] = []

        # 1. Look up built-in tools via registry
        builtin_registry = {}
        if hasattr(self, "config") and self.config:
            from jarvis.tools.registry import ToolRegistry

            registry = ToolRegistry(self.config)
            registry.discover_tools()
            for schema_dict in registry.get_schemas():
                builtin_registry[schema_dict["name"]] = schema_dict

        # 2. Look up MCP tools via platform registry
        mcp_registry = {}
        try:
            from jarvis.mcp.platform.registry import platform_registry

            for tool in platform_registry.tools.values():
                mcp_registry[tool.qualified_name] = {
                    "name": tool.qualified_name,
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "properties": {}},
                    "server": tool.server_name,
                }
        except Exception as e:
            logger.debug("Failed to read MCP platform registry: %s", e)

        for name in names:
            if name in builtin_registry:
                found_schemas[name] = builtin_registry[name]
            elif name in mcp_registry:
                found_schemas[name] = mcp_registry[name]
            else:
                missing_names.append(name)

        if not found_schemas:
            return f"No tools found for requested name(s): {', '.join(names)}"

        output_parts = [f"Retrieved {len(found_schemas)} tool schema(s):\n"]
        for name, info in found_schemas.items():
            output_parts.append(f"### Schema for '{name}'")
            output_parts.append(f"Description: {info.get('description', '')}")
            output_parts.append(f"Parameters Schema:\n```json\n{json.dumps(info.get('parameters', {}), indent=2)}\n```\n")

        if missing_names:
            output_parts.append(f"Note: Could not find schema(s) for: {', '.join(missing_names)}")

        return "\n".join(output_parts)
