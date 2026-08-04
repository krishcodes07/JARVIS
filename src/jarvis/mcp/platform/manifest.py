"""
Manifest loader and validator for MCP server packages.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from jarvis.mcp.platform.models import ServerManifest

logger = logging.getLogger(__name__)


def load_manifest_from_directory(server_dir: Path) -> ServerManifest | None:
    """Load a ``ServerManifest`` from a server directory containing ``manifest.py``.

    Args:
        server_dir: Path to the server package directory.

    Returns:
        A :class:`ServerManifest` object, or ``None`` if the directory is invalid.
    """
    manifest_file = server_dir / "manifest.py"
    if not manifest_file.exists():
        logger.debug("No manifest.py found in %s", server_dir)
        return None

    try:
        module_name = f"jarvis_mcp_server_{server_dir.name}_manifest"
        spec = importlib.util.spec_from_file_location(module_name, manifest_file)
        if not spec or not spec.loader:
            return None

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Look for MANIFEST object or dict
        manifest_obj = getattr(mod, "MANIFEST", None) or getattr(mod, "manifest", None)
        if isinstance(manifest_obj, ServerManifest):
            return manifest_obj
        if isinstance(manifest_obj, dict):
            return ServerManifest(**manifest_obj)

        # Fallback to module-level attributes
        return ServerManifest(
            name=getattr(mod, "NAME", server_dir.name),
            version=getattr(mod, "VERSION", "1.0.0"),
            description=getattr(mod, "DESCRIPTION", ""),
            author=getattr(mod, "AUTHOR", "Anonymous"),
            homepage=getattr(mod, "HOMEPAGE", ""),
            required_env_vars=list(getattr(mod, "REQUIRED_ENV_VARS", [])),
            capabilities=list(getattr(mod, "CAPABILITIES", ["tools", "resources", "prompts"])),
            dependencies=list(getattr(mod, "DEPENDENCIES", [])),
            enabled_by_default=getattr(mod, "ENABLED_BY_DEFAULT", True),
            category=getattr(mod, "CATEGORY", "general"),
        )
    except Exception as e:
        logger.error("Error loading manifest from %s: %s", manifest_file, e)
        return None


def manifest_to_dict(manifest: ServerManifest | None) -> dict[str, Any]:
    """Convert a manifest to a serializable dict (empty dict when None)."""
    return manifest.to_dict() if manifest else {}
