"""
MCP Protocol — transports for connecting to MCP servers.

Wraps the ``mcp`` SDK's transport clients (stdio, SSE, streamable HTTP)
behind a single factory that produces an initialized :class:`ClientSession`
plus an exit stack used to tear it down cleanly.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from jarvis.mcp.platform.models import ServerConfig, TransportType

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when an MCP server connection cannot be established."""


class StdioTransport:
    """Stdio transport for subprocess MCP servers."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    async def open(self, exit_stack: AsyncExitStack) -> ClientSession:
        """Spawn the server subprocess and return an initialized session."""
        server_env = os.environ.copy()
        server_env["PYTHONUNBUFFERED"] = "1"

        for key, value in self.config.env.items():
            if value is not None and str(value).strip() != "":
                server_env[key] = str(value)

        command = self.config.command
        args = list(self.config.args)

        # Always use the current interpreter for python commands
        if command in ("python", "python3", "python.exe"):
            command = sys.executable
            if "-u" not in args:
                args.insert(0, "-u")
        else:
            resolved_cmd = shutil.which(command)
            if resolved_cmd:
                command = resolved_cmd

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=server_env,
        )

        try:
            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
        except FileNotFoundError as e:
            raise MCPConnectionError(
                f"Could not start MCP server '{self.config.name}': "
                f"executable '{command}' not found. {e}"
            ) from e

        read_stream, write_stream = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        return session


class SSETransport:
    """SSE transport for remote MCP servers."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    async def open(self, exit_stack: AsyncExitStack) -> ClientSession:
        from mcp.client.sse import sse_client

        url = self.config.url or "http://localhost:8000/sse"
        try:
            transport = await exit_stack.enter_async_context(sse_client(url))
        except Exception as e:
            raise MCPConnectionError(
                f"Could not connect to SSE MCP server '{self.config.name}' at {url}: {e}"
            ) from e

        read_stream, write_stream = transport
        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        return session


class HTTPTransport:
    """Streamable HTTP transport for remote MCP servers."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    async def open(self, exit_stack: AsyncExitStack) -> ClientSession:
        from mcp.client.streamable_http import streamable_http_client

        url = self.config.url or "http://localhost:8000/mcp"
        try:
            transport = await exit_stack.enter_async_context(streamable_http_client(url))
        except Exception as e:
            raise MCPConnectionError(
                f"Could not connect to HTTP MCP server '{self.config.name}' at {url}: {e}"
            ) from e

        read_stream, write_stream = transport
        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        return session


def create_session(config: ServerConfig, exit_stack: AsyncExitStack) -> Any:
    """Factory that returns a transport instance for the server's transport type.

    Args:
        config: The server configuration.
        exit_stack: The exit stack the transport will use.

    Returns:
        A transport instance exposing ``open(exit_stack) -> ClientSession``.
    """
    if config.transport == TransportType.SSE:
        return SSETransport(config)
    if config.transport == TransportType.HTTP:
        return HTTPTransport(config)
    return StdioTransport(config)
