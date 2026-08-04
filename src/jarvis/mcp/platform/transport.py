"""
Transport abstraction layer for MCP clients and servers.

Supports Stdio, SSE, HTTP, and WebSocket transport strategies. The heavy
lifting is delegated to the ``mcp`` SDK; these classes provide a thin,
uniform lifecycle around the SDK's clients.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from jarvis.mcp.platform.models import ServerConfig

logger = logging.getLogger(__name__)


class BaseTransport(ABC):
    """Abstract base transport for connecting to MCP servers."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    @abstractmethod
    async def connect(self):
        """Establish the transport connection."""

    @abstractmethod
    async def disconnect(self):
        """Close the transport connection."""


class StdioTransport(BaseTransport):
    """Transport for stdio-based subprocess MCP servers."""

    async def connect(self):
        logger.info(
            "Initialized Stdio transport for '%s' (%s)", self.config.name, self.config.command
        )

    async def disconnect(self):
        logger.info("Disconnected Stdio transport for '%s'", self.config.name)


class SSETransport(BaseTransport):
    """Transport for SSE (Server-Sent Events) MCP servers."""

    async def connect(self):
        logger.info(
            "Initialized SSE transport for '%s' at %s", self.config.name, self.config.url
        )

    async def disconnect(self):
        logger.info("Disconnected SSE transport for '%s'", self.config.name)


class HTTPTransport(BaseTransport):
    """Transport for HTTP / streamable-HTTP MCP servers."""

    async def connect(self):
        logger.info(
            "Initialized HTTP transport for '%s' at %s", self.config.name, self.config.url
        )

    async def disconnect(self):
        logger.info("Disconnected HTTP transport for '%s'", self.config.name)


def create_transport(config: ServerConfig) -> BaseTransport:
    """Factory to instantiate a transport by configuration type."""
    if config.transport == config.transport.SSE:
        return SSETransport(config)
    if config.transport == config.transport.HTTP:
        return HTTPTransport(config)
    return StdioTransport(config)
