"""
In-memory platform registry for servers, tools, resources, and prompts.

Allows full indexing, filtering, and searching across all MCP components.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.mcp.platform.models import (
    RegisteredPrompt,
    RegisteredResource,
    RegisteredTool,
    ServerManifest,
)

logger = logging.getLogger(__name__)


class ServerRegistry:
    """Central searchable in-memory registry for the MCP Platform."""

    def __init__(self) -> None:
        self.servers: dict[str, ServerManifest] = {}
        self.tools: dict[str, RegisteredTool] = {}
        self.resources: dict[str, RegisteredResource] = {}
        self.prompts: dict[str, RegisteredPrompt] = {}

    def register_server(self, manifest: ServerManifest) -> None:
        """Register a server manifest."""
        self.servers[manifest.name] = manifest
        logger.info("Registered server in registry: '%s' v%s", manifest.name, manifest.version)

    def register_tool(self, tool: RegisteredTool) -> None:
        """Register an MCP tool."""
        self.tools[tool.qualified_name] = tool
        logger.debug("Registered tool: '%s'", tool.qualified_name)

    def register_resource(self, resource: RegisteredResource) -> None:
        """Register an MCP resource."""
        self.resources[resource.uri] = resource
        logger.debug("Registered resource: '%s'", resource.uri)

    def register_prompt(self, prompt: RegisteredPrompt) -> None:
        """Register an MCP prompt."""
        key = f"{prompt.server_name}__{prompt.name}"
        self.prompts[key] = prompt
        logger.debug("Registered prompt: '%s'", key)

    def clear(self) -> None:
        """Reset the registry."""
        self.servers.clear()
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()

    def unregister_server(self, server_name: str) -> None:
        """Unregister all tools, resources, and prompts for a given server name."""
        self.tools = {
            k: v for k, v in self.tools.items() if v.server_name != server_name
        }
        self.resources = {
            k: v for k, v in self.resources.items() if v.server_name != server_name
        }
        self.prompts = {
            k: v for k, v in self.prompts.items() if v.server_name != server_name
        }
        logger.info("Unregistered tools, resources, and prompts for server: '%s'", server_name)

    # ─── Lookups ──────────────────────────────────────────────

    def has_tool(self, qualified_name: str) -> bool:
        """Return True if a tool with the given qualified name is registered."""
        return qualified_name in self.tools

    def get_tool(self, qualified_name: str) -> RegisteredTool | None:
        """Get a tool by qualified name (``server__tool``)."""
        return self.tools.get(qualified_name)

    def get_resource(self, uri: str) -> RegisteredResource | None:
        """Get a resource by URI."""
        return self.resources.get(uri)

    def get_prompt(self, qualified_name_or_name: str) -> RegisteredPrompt | None:
        """Get a prompt by qualified name or short name."""
        if qualified_name_or_name in self.prompts:
            return self.prompts[qualified_name_or_name]
        for p in self.prompts.values():
            if p.name == qualified_name_or_name:
                return p
        return None

    # ─── Search & filters ─────────────────────────────────────

    def find_tools(
        self, query: str | None = None, server: str | None = None
    ) -> list[RegisteredTool]:
        """Search registered tools by keyword query and/or server filter."""
        results = []
        q = query.lower() if query else None
        for tool in self.tools.values():
            if server and tool.server_name.lower() != server.lower():
                continue
            if q and q not in tool.name.lower() and q not in tool.description.lower():
                continue
            results.append(tool)
        return results

    def find_resources(
        self, query: str | None = None, server: str | None = None
    ) -> list[RegisteredResource]:
        """Search registered resources by keyword query and/or server filter."""
        results = []
        q = query.lower() if query else None
        for resource in self.resources.values():
            if server and resource.server_name.lower() != server.lower():
                continue
            if q and (
                q not in resource.uri.lower()
                and q not in resource.name.lower()
                and q not in resource.description.lower()
            ):
                continue
            results.append(resource)
        return results

    def find_prompts(
        self, query: str | None = None, server: str | None = None
    ) -> list[RegisteredPrompt]:
        """Search registered prompts by keyword query and/or server filter."""
        results = []
        q = query.lower() if query else None
        for prompt in self.prompts.values():
            if server and prompt.server_name.lower() != server.lower():
                continue
            if q and q not in prompt.name.lower() and q not in prompt.description.lower():
                continue
            results.append(prompt)
        return results

    # ─── OpenAI-format export ─────────────────────────────────

    def get_all_tools_openai_format(self) -> list[dict[str, Any]]:
        """Convert all registered tools to OpenAI function-calling JSON format."""
        tools_list: list[dict[str, Any]] = []
        for tool in self.tools.values():
            tools_list.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.qualified_name,
                        "description": tool.description,
                        "parameters": tool.input_schema
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools_list


# Global platform registry singleton instance
platform_registry = ServerRegistry()
