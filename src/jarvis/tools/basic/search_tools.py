"""
Search Tools Tool — Dynamic Meta-Tool for tool discovery and retrieval.

Enables the LLM to search for tools by keyword, acronym, or capability intent
(e.g., 'telegram', 'tg', 'scrape web', 'firecrawl') when schema is not loaded in prompt context.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class SearchToolsTool(BaseTool):
    """Search registered tools and MCP tools dynamically by query or capability keyword."""

    schema = ToolSchema(
        name="search_tools",
        description=(
            "Search for available tools and MCP server capabilities by capability keyword, acronym, "
            "or intent (e.g. 'telegram', 'tg', 'scrape web', 'firecrawl', 'file search'). "
            "Returns matching tool schemas and descriptions."
        ),
        category="basic",
        aliases=["find_tool", "discover_tools", "tool_search"],
        keywords=["search", "tool", "capability", "mcp", "discover"],
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query, capability keyword, or acronym to find relevant tools for.",
                required=True,
            )
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Search and return tool definitions matching query."""
        query = kwargs.get("query", "").strip()
        if not query:
            return "Please provide a non-empty search query."

        try:
            from jarvis.providers.base import ToolDefinition

            all_defs: list[ToolDefinition] = []

            # 1. Built-in tools via ToolRegistry
            if hasattr(self, "config") and self.config:
                from jarvis.tools.registry import ToolRegistry
                registry = ToolRegistry(self.config)
                registry.discover_tools()
                for tool_inst in registry._tools.values():
                    all_defs.append(
                        ToolDefinition(
                            name=tool_inst.name,
                            description=tool_inst.description,
                            parameters=tool_inst.schema.to_json_schema(),
                            aliases=getattr(tool_inst.schema, "aliases", []),
                            category=getattr(tool_inst.schema, "category", "basic"),
                            keywords=getattr(tool_inst.schema, "keywords", []),
                        )
                    )

            query_lower = query.lower()

            # 2. Filter & score tools by keyword/alias and semantic match
            matches: list[tuple[float, ToolDefinition]] = []
            for t in all_defs:
                score = 0.0
                # Exact name or alias match
                if query_lower == t.name.lower():
                    score += 10.0
                elif query_lower in [a.lower() for a in t.aliases]:
                    score += 9.0
                elif any(query_lower in a.lower() for a in t.aliases):
                    score += 5.0
                elif query_lower in t.name.lower():
                    score += 4.0
                elif query_lower in t.description.lower():
                    score += 2.0
                elif any(query_lower in k.lower() for k in t.keywords):
                    score += 3.0

                if score > 0:
                    matches.append((score, t))

            matches.sort(key=lambda x: x[0], reverse=True)

            if not matches:
                return f"No tools found matching query '{query}'. Try broader terms like 'web', 'file', 'system', 'code'."

            lines = [f"Found {len(matches)} tool(s) matching '{query}':\n"]
            for _, tool in matches[:5]:
                lines.append(f"### Tool: {tool.name}")
                lines.append(f"Description: {tool.description}")
                if tool.aliases:
                    lines.append(f"Aliases: {', '.join(tool.aliases)}")
                lines.append(f"Parameters Schema: {tool.parameters}\n")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Failed to execute search_tools: {e}")
            return f"Error searching tools: {e}"
