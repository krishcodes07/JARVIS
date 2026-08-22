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

from jarvis.core.config import CONFIG_DIR

logger = logging.getLogger(__name__)

# Default server catalog shipped inside the ``jarvis.mcp`` package. Resolved
# relative to this module so it works from a source checkout, an editable
# install and a site-packages install alike.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "servers.json"


def get_user_mcp_config_path() -> Path:
    """Get the user-level MCP configuration path (~/.jarvis/mcp/servers.json)."""
    try:
        from jarvis.core.paths import get_jarvis_home
        return get_jarvis_home() / "mcp" / "servers.json"
    except Exception:
        from jarvis.core.config import CONFIG_DIR
        return CONFIG_DIR / "mcp_servers.json"


def get_default_mcp_config_path(config: Any | None = None) -> Path:
    """Resolve the catalog path to load server definitions from.

    Honors ``config.mcp.servers_config`` when set, so a deployment can point
    JARVIS at its own catalog. Relative paths resolve against the JARVIS data
    root; an empty value means "use the catalog shipped with the package".

    Args:
        config: A :class:`~jarvis.core.config.JarvisConfig`, if available.

    Returns:
        Path to the catalog JSON file.
    """
    configured = ""
    if config is not None:
        configured = str(getattr(getattr(config, "mcp", None), "servers_config", "") or "")

    if not configured.strip():
        return DEFAULT_CONFIG_PATH

    from jarvis.core.paths import resolve_data_path

    return resolve_data_path(configured.strip())


def __getattr__(name: str) -> Any:
    """Resolve ``USER_CONFIG_PATH`` lazily.

    Evaluating it at import time would freeze the path before a caller had a
    chance to set ``JARVIS_HOME``.
    """
    if name == "USER_CONFIG_PATH":
        return get_user_mcp_config_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class MCPRegistry:
    """Registry of configured MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, dict[str, Any]] = {}

    def load(
        self,
        default_path: Path | None = None,
        user_path: Path | None = None,
        config: Any | None = None,
    ) -> None:
        """Load server configurations from default template and user config files.

        Precedence:
        1. User config at ~/.jarvis/mcp/servers.json (highest)
        2. Legacy user config at config/mcp_servers.json (for migration)
        3. Default catalog — ``config.mcp.servers_config`` if set, else the one
           shipped in the ``jarvis.mcp`` package (fallback catalog)

        Args:
            default_path: Explicit catalog path, overriding config and package default.
            user_path: Explicit user config path.
            config: A :class:`~jarvis.core.config.JarvisConfig` whose
                ``mcp.servers_config`` selects the catalog.
        """
        if default_path is None:
            default_path = get_default_mcp_config_path(config)
        if user_path is None:
            user_path = get_user_mcp_config_path()

        merged: dict[str, dict[str, Any]] = {}

        # 1. Base package template
        if default_path and default_path.exists():
            try:
                data = json.loads(default_path.read_text(encoding="utf-8"))
                servers = data.get("servers", data.get("mcpServers", {}))
                if isinstance(servers, dict):
                    merged.update(servers)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse default MCP config %s: %s", default_path, e)

        # 2. Legacy config/mcp_servers.json if user_path does not exist yet
        legacy_path = CONFIG_DIR / "mcp_servers.json"
        if not user_path.exists() and legacy_path.exists():
            try:
                data = json.loads(legacy_path.read_text(encoding="utf-8"))
                servers = data.get("servers", data.get("mcpServers", {}))
                if isinstance(servers, dict):
                    merged.update(servers)
                    logger.info("Migrated %d MCP server configs from %s", len(servers), legacy_path)
            except Exception as e:
                logger.warning("Failed to migrate legacy MCP config %s: %s", legacy_path, e)

        # 3. User config at ~/.jarvis/mcp/servers.json (primary source of truth)
        if user_path and user_path.exists():
            try:
                data = json.loads(user_path.read_text(encoding="utf-8"))
                servers = data.get("servers", data.get("mcpServers", {}))
                if isinstance(servers, dict):
                    merged.update(servers)
                    logger.info("Loaded %d MCP server configs from %s", len(servers), user_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse user MCP config %s: %s", user_path, e)

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
        """Persist current server configurations to the user-level config file (~/.jarvis/mcp/servers.json)."""
        if path is None:
            path = get_user_mcp_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"servers": self._servers}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Saved %d MCP server configs to %s", len(self._servers), path)

    def __len__(self) -> int:
        return len(self._servers)
