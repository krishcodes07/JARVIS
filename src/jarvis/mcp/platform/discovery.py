"""
Automatic server discovery engine.

Scans configured server locations for self-contained MCP server packages
(directories containing a ``manifest.py``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from jarvis.core.config import PROJECT_ROOT
from jarvis.mcp.platform.manifest import load_manifest_from_directory
from jarvis.mcp.platform.models import ServerManifest

logger = logging.getLogger(__name__)

# Default location of built-in server packages.
DEFAULT_SERVERS_DIR = PROJECT_ROOT / "src" / "jarvis" / "mcp" / "servers"


class ServerDiscoveryEngine:
    """Discovers MCP server packages dynamically from the filesystem."""

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        if search_paths is None:
            search_paths = [DEFAULT_SERVERS_DIR]
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
