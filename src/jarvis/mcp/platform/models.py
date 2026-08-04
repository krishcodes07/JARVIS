"""
Data models for the JARVIS MCP Platform framework.

Defines schemas for Manifests, Server Configurations, Tools, Resources,
Prompts, and Transports. These mirror the standard MCP concepts and are
shared between the client (JARVIS) and the server packages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TransportType(str, Enum):
    """Supported MCP transport strategies."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


class ServerStatus(str, Enum):
    """Lifecycle status of an MCP server connection."""

    STOPPED = "stopped"
    STARTING = "starting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ServerManifest:
    """Metadata describing an MCP server package."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "Anonymous"
    homepage: str = ""
    required_env_vars: list[str] = field(default_factory=list)
    capabilities: list[str] = field(
        default_factory=lambda: ["tools", "resources", "prompts"]
    )
    dependencies: list[str] = field(default_factory=list)
    enabled_by_default: bool = True
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest to a plain dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "required_env_vars": self.required_env_vars,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "enabled_by_default": self.enabled_by_default,
            "category": self.category,
        }


@dataclass
class ServerConfig:
    """Configuration for launching or connecting to an MCP server."""

    name: str
    enabled: bool = True
    transport: TransportType = TransportType.STDIO
    command: str = "python"
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    auto_restart: bool = True
    url: str | None = None  # For HTTP/SSE/Remote transport
    description: str = ""


@dataclass
class RegisteredTool:
    """Represents a discovered and registered MCP tool."""

    name: str
    qualified_name: str
    description: str
    server_name: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    func: Callable | None = None


@dataclass
class RegisteredResource:
    """Represents a discovered and registered MCP resource."""

    uri: str
    name: str
    description: str
    server_name: str
    mime_type: str = "text/plain"
    func: Callable | None = None


@dataclass
class RegisteredPromptArgument:
    """Argument specification for an MCP prompt."""

    name: str
    description: str = ""
    required: bool = True


@dataclass
class RegisteredPrompt:
    """Represents a discovered and registered MCP prompt template."""

    name: str
    description: str
    server_name: str
    template: str = ""
    arguments: list[RegisteredPromptArgument] = field(default_factory=list)
    func: Callable | None = None
