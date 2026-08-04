"""
MCP Registry — Manages MCP server configurations.

Loads server configurations from the default package ``servers.json`` and
merges any user-level overrides stored at ``config/mcp_servers.json``.
Servers added/updated at runtime (e.g. by the installer) are persisted to the
user-level file so package data stays pristine.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jarvis.core.config import CONFIG_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Default server configurations shipped with the package.
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "src" / "jarvis" / "mcp" / "servers.json"
# User-level overrides / installed servers.
USER_CONFIG_PATH = CONFIG_DIR / "mcp_servers.json"


class MCPRegistry:
    """Registry of configured MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, dict[str, Any]] = {}

    def load(self, default_path: Path | None = None, user_path: Path | None = None) -> None:
        """Load server configurations from default and user config files."""
        if default_path is None:
            default_path = DEFAULT_CONFIG_PATH
        if user_path is None:
            user_path = USER_CONFIG_PATH

        merged: dict[str, dict[str, Any]] = {}
        for path in (default_path, user_path):
            if path and path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to parse MCP config %s: %s", path, e)
                    continue
                servers = data.get("servers", data.get("mcpServers", {}))
                if isinstance(servers, dict):
                    merged.update(servers)
                    logger.info("Loaded %d MCP server configs from %s", len(servers), path)

        self._servers = merged

    def get(self, name: str) -> dict[str, Any]:
        """Get a server configuration by name.

        Raises:
            KeyError: If the server is not configured.
        """
        if name not in self._servers:
            raise KeyError(f"MCP server '{name}' not configured.")
        return self._servers[name]

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Get all server configurations keyed by name."""
        return dict(self._servers)

    def list_servers(self) -> list[str]:
        """List all configured server names."""
        return list(self._servers.keys())

    def register(self, name: str, config: dict[str, Any]) -> None:
        """Register or update a server configuration."""
        self._servers[name] = config

    def remove(self, name: str) -> None:
        """Remove a server configuration."""
        self._servers.pop(name, None)

    def save_user_config(self, path: Path | None = None) -> None:
        """Persist current server configurations to the user-level config file."""
        if path is None:
            path = USER_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"servers": self._servers}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Saved %d MCP server configs to %s", len(self._servers), path)

    def __len__(self) -> int:
        return len(self._servers)
