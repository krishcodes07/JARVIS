"""
Automatic server discovery engine.

Scans configured server locations for self-contained MCP server packages
(directories containing a ``manifest.py``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from jarvis.mcp.platform.manifest import load_manifest_from_directory
from jarvis.mcp.platform.models import ServerManifest

logger = logging.getLogger(__name__)

# Built-in server packages live next to this module inside ``jarvis.mcp``.
# Resolved from ``__file__`` so discovery works from a source checkout, an
# editable install and a site-packages install alike.
DEFAULT_SERVERS_DIR = Path(__file__).resolve().parent.parent / "servers"


def get_user_servers_dir() -> Path:
    """User-installed server packages directory (~/.jarvis/mcp/servers)."""
    from jarvis.core.paths import get_jarvis_home

    return get_jarvis_home() / "mcp" / "servers"


def default_search_paths() -> list[Path]:
    """Default discovery locations: built-in packages, then user-installed ones."""
    return [DEFAULT_SERVERS_DIR, get_user_servers_dir()]


class ServerDiscoveryEngine:
    """Discovers MCP server packages dynamically from the filesystem."""

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        if search_paths is None:
            search_paths = default_search_paths()
        self.search_paths = [p.resolve() for p in search_paths if p.exists()]

    def discover_servers(self) -> dict[str, ServerManifest]:
        """Scan all search paths for directories containing ``manifest.py``.

        Returns:
            Dict mapping server name to :class:`ServerManifest`.
        """
        discovered: dict[str, ServerManifest] = {}

        for search_path in self.search_paths:
            logger.info("Scanning directory for MCP server packages: %s", search_path)
            if not search_path.is_dir():
                continue

            for entry in search_path.iterdir():
                # Ignore hidden folders, __pycache__, and _template
                if not entry.is_dir() or entry.name.startswith((".", "_")):
                    continue

                manifest = load_manifest_from_directory(entry)
                if manifest and manifest.name not in discovered:
                    discovered[manifest.name] = manifest
                    logger.info(
                        "Discovered server: '%s' (%s) at %s",
                        manifest.name,
                        manifest.version,
                        entry,
                    )

        return discovered
