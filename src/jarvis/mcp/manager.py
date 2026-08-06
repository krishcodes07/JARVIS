"""
MCP Manager — orchestrates MCP server lifecycle and exposes MCP capabilities.

Responsibilities:
- Load server configuration (servers.json + user overrides + auto-discovery)
- Connect to enabled servers via :class:`jarvis.mcp.client.MCPClient`
- Register all discovered tools/resources/prompts in the platform registry
- Provide engine-facing APIs (tool definitions, tool calls, resources, prompts)
- Graceful shutdown of all server connections
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from jarvis.core.exceptions import MCPError
from jarvis.mcp.client import MCPClient
from jarvis.mcp.platform.discovery import ServerDiscoveryEngine
from jarvis.mcp.platform.hooks import PlatformHooksManager
from jarvis.mcp.platform.models import (
    ServerConfig,
    ServerManifest,
    TransportType,
)
from jarvis.mcp.platform.registry import platform_registry
from jarvis.mcp.registry import MCPRegistry
from jarvis.providers.base import ToolDefinition

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages MCP server lifecycle and exposes MCP capabilities to JARVIS."""

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self.registry = MCPRegistry()
        self.client = MCPClient()
        self._manifests: dict[str, ServerManifest] = {}

    @property
    def servers(self) -> dict[str, Any]:
        """Mapping of server name to active connection."""
        return self.client.connections

    async def initialize(self) -> None:
        """Initialize the MCP subsystem and connect to enabled servers."""
        if not self.config.mcp.enabled:
            logger.info("MCP is disabled.")
            return

        self.registry.load()

        # Auto-discovery of all server packages in servers/ (auto-register everything).
        discovery = ServerDiscoveryEngine()
        self._manifests = discovery.discover_servers()
        for manifest in self._manifests.values():
            platform_registry.register_server(manifest)

        server_configs = self._build_server_configs()
        if not server_configs:
            logger.info("No MCP servers enabled.")
            return

        for server_config in server_configs:
            manifest = self._manifests.get(server_config.name)
            if manifest and manifest.required_env_vars:
                ok, missing = PlatformHooksManager.check_environment(manifest, dict(os.environ))
                if not ok:
                    logger.warning(
                        "Skipping MCP server '%s': missing env vars %s",
                        server_config.name,
                        missing,
                    )
                    continue
            try:
                await self.client.connect(server_config)
            except Exception as e:
                logger.warning("Failed to connect MCP server '%s': %s", server_config.name, e)

    async def shutdown(self) -> None:
        """Disconnect from all MCP servers and clear the registry."""
        await self.client.disconnect_all()
        logger.info("MCP manager shut down.")

    # ─── Server configuration ─────────────────────────────────

    def _build_server_configs(self) -> list[ServerConfig]:
        """Build the list of enabled :class:`ServerConfig` objects.

        Every server package discovered in ``servers/`` is auto-registered.
        Per-server settings are merged with the following precedence
        (highest first):

        1. ``jarvis.yaml`` → ``mcp.servers.<name>`` overrides
        2. Registry config (``servers.json`` / user ``mcp_servers.json``)
        3. Server manifest defaults (``enabled_by_default``)

        Honors ``mcp.auto_start`` when non-empty (connect only those).
        """
        auto_start = [name.lower() for name in self.config.mcp.auto_start]
        overrides = self.config.mcp.servers

        # Base set: every discovered package plus any registry-configured
        # servers that aren't on disk (e.g. npm/pip/git installed).
        names = set(self._manifests.keys())
        names.update(self.registry.get_all().keys())

        configs: list[ServerConfig] = []
        for name in sorted(names):
            if auto_start and name.lower() not in auto_start:
                logger.debug("MCP server '%s' not in auto_start list; skipping.", name)
                continue

            manifest = self._manifests.get(name)
            entry = self.registry.get_all().get(name, {})
            override = overrides.get(name)

            # Enabled precedence: jarvis.yaml > registry > manifest default.
            enabled = (
                override.enabled
                if override is not None and override.enabled is not None
                else entry.get(
                    "enabled", manifest.enabled_by_default if manifest else True
                )
            )
            if not enabled:
                logger.debug("MCP server '%s' is disabled; skipping.", name)
                continue

            transport_str = (
                override.transport
                if override is not None and override.transport
                else str(entry.get("transport", "stdio")).lower()
            )
            try:
                transport = TransportType(transport_str)
            except ValueError:
                transport = TransportType.STDIO

            # Auto-registered servers default to a python-module launch.
            command = (
                override.command
                if override is not None and override.command
                else entry.get("command", "python")
            )
            args = list(
                override.args
                if override is not None and override.args
                else entry.get("args", [])
            )
            if not args and manifest:
                args = ["-m", f"jarvis.mcp.servers.{name}.server"]

            env = dict(entry.get("env", {}))
            env.update(override.env if override else {})

            configs.append(
                ServerConfig(
                    name=name,
                    enabled=True,
                    transport=transport,
                    command=command,
                    args=args,
                    env=env,
                    timeout=int(
                        override.timeout
                        if override is not None and override.timeout is not None
                        else entry.get("timeout", self.config.mcp.timeout)
                    ),
                    auto_restart=bool(entry.get("auto_restart", True)),
                    url=override.url if override else entry.get("url"),
                    description=(
                        override.description
                        if override is not None and override.description
                        else entry.get("description", "")
                    ),
                )
            )

        return configs

    def register_server_config(self, name: str, config: dict[str, Any]) -> None:
        """Register or update a server configuration (used by the installer)."""
        self.registry.register(name, config)
        self.registry.save_user_config()

    def get_available_servers(self) -> list[dict[str, Any]]:
        """List all discoverable server packages and registry configured servers."""
        overrides = self.config.mcp.servers
        registry_servers = self.registry.get_all()

        names = set(self._manifests.keys())
        names.update(registry_servers.keys())

        available: list[dict[str, Any]] = []
        for name in sorted(names):
            manifest = self._manifests.get(name)
            entry = registry_servers.get(name, {})
            override = overrides.get(name)

            enabled = (
                override.enabled
                if override is not None and override.enabled is not None
                else entry.get("enabled", manifest.enabled_by_default if manifest else True)
            )

            desc = (
                override.description
                if override is not None and override.description
                else entry.get("description", manifest.description if manifest else "")
            )

            version = manifest.version if manifest else entry.get("version", "1.0.0")

            available.append(
                {
                    "name": name,
                    "version": version,
                    "description": desc,
                    "enabled": enabled,
                    "configured": name in registry_servers,
                }
            )
        return available

    def get_server_config(self, name: str, force_enabled: bool = True) -> ServerConfig | None:
        """Build a ServerConfig object for a server by name from registry, manifest, or overrides."""
        manifest = self._manifests.get(name)
        entry = self.registry.get_all().get(name, {})
        override = self.config.mcp.servers.get(name)

        if not manifest and not entry:
            return None

        enabled = True if force_enabled else (
            override.enabled
            if override is not None and override.enabled is not None
            else entry.get("enabled", manifest.enabled_by_default if manifest else True)
        )

        transport_str = (
            override.transport
            if override is not None and override.transport
            else str(entry.get("transport", "stdio")).lower()
        )
        try:
            transport = TransportType(transport_str)
        except ValueError:
            transport = TransportType.STDIO

        command = (
            override.command
            if override is not None and override.command
            else entry.get("command", "python")
        )
        args = list(
            override.args
            if override is not None and override.args
            else entry.get("args", [])
        )
        if not args and manifest:
            args = ["-m", f"jarvis.mcp.servers.{name}.server"]

        env = dict(entry.get("env", {}))
        if override and override.env:
            env.update(override.env)

        return ServerConfig(
            name=name,
            enabled=enabled,
            transport=transport,
            command=command,
            args=args,
            env=env,
            timeout=int(
                override.timeout
                if override is not None and override.timeout is not None
                else entry.get("timeout", self.config.mcp.timeout)
            ),
            auto_restart=bool(entry.get("auto_restart", True)),
            url=override.url if override else entry.get("url"),
            description=(
                override.description
                if override is not None and override.description
                else entry.get("description", manifest.description if manifest else "")
            ),
        )

    # ─── Tools (engine-facing) ────────────────────────────────

    def has_tool(self, qualified_name: str) -> bool:
        """Return True if an MCP tool with the given qualified name is registered."""
        return platform_registry.has_tool(qualified_name)

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all registered MCP tools as OpenAI-format dicts."""
        return platform_registry.get_all_tools_openai_format()

    def get_all_tool_definitions(self) -> list[ToolDefinition]:
        """Get all registered MCP tools as engine ``ToolDefinition`` objects."""
        definitions: list[ToolDefinition] = []
        for tool in platform_registry.tools.values():
            definitions.append(
                ToolDefinition(
                    name=tool.qualified_name,
                    description=tool.description,
                    parameters=tool.input_schema
                    or {"type": "object", "properties": {}},
                )
            )
        return definitions

    async def call_tool(
        self, qualified_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool call routed to the correct MCP server.

        Args:
            qualified_name: The qualified tool name (``server__tool``).
            arguments: Tool arguments.

        Returns:
            The tool result text.

        Raises:
            MCPError: If the tool or its server is unavailable.
        """
        registered = platform_registry.get_tool(qualified_name)
        if not registered:
            raise MCPError(f"Unknown MCP tool: '{qualified_name}'")

        try:
            return await self.client.call_tool(
                registered.server_name, registered.name, arguments
            )
        except Exception as e:
            raise MCPError(
                f"Failed to call MCP tool '{qualified_name}': {e}"
            ) from e

    # ─── Resources & prompts ──────────────────────────────────

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI from its hosting MCP server."""
        registered = platform_registry.get_resource(uri)
        if not registered:
            raise MCPError(f"Unknown MCP resource URI: '{uri}'")
        try:
            return await self.client.read_resource(registered.server_name, uri)
        except Exception as e:
            raise MCPError(f"Failed to read MCP resource '{uri}': {e}") from e

    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Get a rendered prompt template from its hosting MCP server."""
        registered = platform_registry.get_prompt(name)
        if not registered:
            raise MCPError(f"Unknown MCP prompt: '{name}'")
        try:
            return await self.client.get_prompt(
                registered.server_name, registered.name, arguments or {}
            )
        except Exception as e:
            raise MCPError(f"Failed to get MCP prompt '{name}': {e}") from e

    def get_resources(self) -> list[dict[str, Any]]:
        """List all registered MCP resources."""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "server": r.server_name,
                "mime_type": r.mime_type,
            }
            for r in platform_registry.resources.values()
        ]

    def get_prompts(self) -> list[dict[str, Any]]:
        """List all registered MCP prompts."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "server": p.server_name,
                "arguments": [
                    {"name": a.name, "description": a.description, "required": a.required}
                    for a in p.arguments
                ],
            }
            for p in platform_registry.prompts.values()
        ]

    def get_server_info(self) -> list[dict[str, Any]]:
        """Get summary info about all configured servers."""
        info: list[dict[str, Any]] = []
        for name, conn in self.client.connections.items():
            manifest = platform_registry.servers.get(name)
            info.append(
                {
                    "name": conn.name,
                    "version": manifest.version if manifest else "1.0.0",
                    "description": (
                        conn.config.description
                        or (manifest.description if manifest else "")
                    ),
                    "tools_count": len(conn.tools),
                    "resources_count": len(conn.resources),
                    "prompts_count": len(conn.prompts),
                    "status": "connected" if conn.connected else f"error: {conn.error or 'failed'}",
                }
            )
        return info
