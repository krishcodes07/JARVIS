"""
MCP Client — connects to and communicates with MCP servers.

Handles the full lifecycle of a server connection:
- Spawning/connecting transports (stdio, SSE, streamable HTTP)
- Discovering tools, resources, and prompts
- Invoking tools and reading resources/prompts
- Clean shutdown of all active connections

Each connection registers its discovered components in the shared
:data:`jarvis.mcp.platform.registry.platform_registry`.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from jarvis.mcp.platform.models import (
    RegisteredPrompt,
    RegisteredPromptArgument,
    RegisteredResource,
    RegisteredTool,
    ServerConfig,
)
from jarvis.mcp.platform.registry import platform_registry
from jarvis.mcp.protocol import MCPConnectionError, create_session

logger = logging.getLogger(__name__)


@dataclass
class ServerConnection:
    """Tracks an active connection to a single MCP server."""

    name: str
    config: ServerConfig
    session: Any | None = None
    tools: list = field(default_factory=list)
    resources: list = field(default_factory=list)
    prompts: list = field(default_factory=list)
    connected: bool = False
    error: str | None = None
    exit_stack: AsyncExitStack = field(default_factory=AsyncExitStack)


class MCPClient:
    """Client for connecting to MCP (Model Context Protocol) servers."""

    def __init__(self) -> None:
        self._connections: dict[str, ServerConnection] = {}

    @property
    def connections(self) -> dict[str, ServerConnection]:
        """Mapping of server name to active connection."""
        return self._connections

    async def connect(self, config: ServerConfig) -> ServerConnection:
        """Connect to an MCP server and discover its components.

        Args:
            config: The server configuration.

        Returns:
            A :class:`ServerConnection` tracking the connection.

        Raises:
            MCPConnectionError: If the connection fails.
        """
        if config.name in self._connections and self._connections[config.name].connected:
            return self._connections[config.name]

        conn = ServerConnection(name=config.name, config=config)
        self._connections[config.name] = conn

        try:
            await self._connect_single(config, conn)
        except Exception as e:
            conn.connected = False
            conn.error = str(e)
            logger.warning("MCP server '%s' failed to connect: %s", config.name, e)
            await conn.exit_stack.aclose()
            raise MCPConnectionError(f"'{config.name}': {e}") from e

        return conn

    async def _connect_single(self, config: ServerConfig, conn: ServerConnection) -> None:
        """Connect to a single MCP server and register its components."""
        await conn.exit_stack.__aenter__()

        transport = create_session(config, conn.exit_stack)
        try:
            session = await asyncio.wait_for(
                transport.open(conn.exit_stack),
                timeout=float(config.timeout),
            )
        except TimeoutError as e:
            raise MCPConnectionError(
                f"Connection timed out after {config.timeout}s"
            ) from e

        conn.session = session
        conn.connected = True

        # 1. Discover tools
        try:
            tools_resp = await session.list_tools()
            conn.tools = list(tools_resp.tools)
            for tool in conn.tools:
                schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
                if hasattr(schema, "model_dump"):
                    schema = schema.model_dump()
                if not isinstance(schema, dict):
                    schema = {"type": "object", "properties": {}}

                qualified_name = f"{config.name}__{tool.name}"
                platform_registry.register_tool(
                    RegisteredTool(
                        name=tool.name,
                        qualified_name=qualified_name,
                        description=tool.description
                        or f"Tool '{tool.name}' from '{config.name}'",
                        server_name=config.name,
                        input_schema=schema,
                    )
                )
        except Exception as e:
            logger.warning("Server '%s' tools discovery failed: %s", config.name, e)

        # 2. Discover resources
        try:
            res_resp = await session.list_resources()
            conn.resources = list(res_resp.resources)
            for res in conn.resources:
                platform_registry.register_resource(
                    RegisteredResource(
                        uri=str(res.uri),
                        name=res.name or str(res.uri),
                        description=res.description or f"Resource {res.uri}",
                        server_name=config.name,
                        mime_type=getattr(res, "mimeType", "text/plain"),
                    )
                )
        except Exception as e:
            logger.debug("Server '%s' resources discovery: %s", config.name, e)

        # 3. Discover prompts
        try:
            prompt_resp = await session.list_prompts()
            conn.prompts = list(prompt_resp.prompts)
            for p in conn.prompts:
                args_spec = [
                    RegisteredPromptArgument(
                        name=arg.name,
                        description=getattr(arg, "description", ""),
                        required=getattr(arg, "required", True),
                    )
                    for arg in getattr(p, "arguments", [])
                ]
                platform_registry.register_prompt(
                    RegisteredPrompt(
                        name=p.name,
                        description=p.description or f"Prompt template '{p.name}'",
                        server_name=config.name,
                        arguments=args_spec,
                    )
                )
        except Exception as e:
            logger.debug("Server '%s' prompts discovery: %s", config.name, e)

        logger.info(
            "MCP server '%s' connected: %d tools, %d resources, %d prompts",
            config.name,
            len(conn.tools),
            len(conn.resources),
            len(conn.prompts),
        )

    # ─── Tool calls ───────────────────────────────────────────

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Call a tool on a specific MCP server.

        Args:
            server_name: The server name.
            tool_name: The tool name (unqualified).
            arguments: Tool arguments.

        Returns:
            The tool result text.

        Raises:
            RuntimeError: If the server is not connected.
        """
        conn = self._get_connection(server_name)
        assert conn.session is not None
        try:
            result = await conn.session.call_tool(tool_name, arguments or {})
        except Exception as e:
            logger.error(
                "Tool call failed - %s on %s: %s", tool_name, server_name, e
            )
            raise

        output_parts = []
        for content_block in result.content:
            if hasattr(content_block, "text"):
                output_parts.append(content_block.text)
            else:
                output_parts.append(str(content_block))
        return "\n".join(output_parts)

    async def read_resource(self, server_name: str, uri: str) -> str:
        """Read a resource from an MCP server.

        Args:
            server_name: The server name.
            uri: The resource URI.

        Returns:
            The resource content text.
        """
        conn = self._get_connection(server_name)
        assert conn.session is not None
        try:
            result = await conn.session.read_resource(uri)
        except Exception as e:
            logger.error("Read resource failed - %s on %s: %s", uri, server_name, e)
            raise

        parts = []
        for item in result.contents:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)

    async def get_prompt(
        self, server_name: str, prompt_name: str, arguments: dict[str, Any] | None = None
    ) -> str:
        """Get a rendered prompt from an MCP server.

        Args:
            server_name: The server name.
            prompt_name: The prompt name.
            arguments: Optional arguments for the prompt template.

        Returns:
            The rendered prompt text.
        """
        conn = self._get_connection(server_name)
        assert conn.session is not None
        try:
            result = await conn.session.get_prompt(prompt_name, arguments or {})
        except Exception as e:
            logger.error("Get prompt failed - %s on %s: %s", prompt_name, server_name, e)
            raise

        parts = []
        for msg in result.messages:
            content = getattr(msg, "content", "")
            if hasattr(content, "text"):
                content_text = content.text
            elif isinstance(content, dict):
                content_text = content.get("text", str(content))
            else:
                content_text = str(content)
            parts.append(f"[{getattr(msg, 'role', 'user')}]: {content_text}")
        return "\n".join(parts)

    # ─── Lifecycle ────────────────────────────────────────────

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server and unregister its components."""
        conn = self._connections.pop(server_name, None)
        if conn:
            if conn.connected or conn.session:
                try:
                    await conn.exit_stack.aclose()
                except Exception as e:
                    logger.debug("Exit stack closed for %s: %s", server_name, e)
            logger.info("Disconnected from MCP server: %s", server_name)
        platform_registry.unregister_server(server_name)

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers and clear the platform registry."""
        for name in list(self._connections.keys()):
            await self.disconnect(name)
        platform_registry.clear()

    def _get_connection(self, server_name: str) -> ServerConnection:
        """Return a connected connection or raise a clear error."""
        conn = self._connections.get(server_name)
        if not conn or not conn.connected or not conn.session:
            raise RuntimeError(
                f"MCP server '{server_name}' is not connected."
            )
        return conn
