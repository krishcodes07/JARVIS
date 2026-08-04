"""
JARVIS MCP Platform — dynamic MCP server packages.

The platform lets JARVIS treat MCP servers as self-contained packages with a
``manifest.py``, ``config.py``, ``server.py`` and ``tools/``, ``resources/``,
``prompts/`` folders. Servers are auto-discovered and built into FastMCP
instances, while the client discovers their tools/resources/prompts at
connection time.
"""

from jarvis.mcp.platform.discovery import DEFAULT_SERVERS_DIR, ServerDiscoveryEngine
from jarvis.mcp.platform.loader import ServerPackageLoader
from jarvis.mcp.platform.manifest import load_manifest_from_directory
from jarvis.mcp.platform.models import (
    RegisteredPrompt,
    RegisteredPromptArgument,
    RegisteredResource,
    RegisteredTool,
    ServerConfig,
    ServerManifest,
    ServerStatus,
    TransportType,
)
from jarvis.mcp.platform.registry import ServerRegistry, platform_registry
from jarvis.mcp.platform.runner import create_server_from_package

__all__ = [
    "DEFAULT_SERVERS_DIR",
    "RegisteredPrompt",
    "RegisteredPromptArgument",
    "RegisteredResource",
    "RegisteredTool",
    "ServerConfig",
    "ServerDiscoveryEngine",
    "ServerManifest",
    "ServerPackageLoader",
    "ServerRegistry",
    "ServerStatus",
    "TransportType",
    "create_server_from_package",
    "load_manifest_from_directory",
    "platform_registry",
]
