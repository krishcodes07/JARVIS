"""
Platform hooks and extensibility layer.

Provides hooks for authentication, permissions, capability negotiation,
and environment validation for MCP server packages.
"""

from __future__ import annotations

import logging

from jarvis.mcp.platform.models import ServerManifest

logger = logging.getLogger(__name__)


class PlatformHooksManager:
    """Manages platform lifecycle hooks and security checks."""

    @staticmethod
    def check_version_compatibility(
        manifest: ServerManifest, min_platform_version: str = "1.0.0"
    ) -> bool:
        """Verify server version compatibility (simple semver placeholder)."""
        logger.debug("Checked version for '%s': v%s", manifest.name, manifest.version)
        return True

    @staticmethod
    def validate_permissions(manifest: ServerManifest, requested_capability: str) -> bool:
        """Validate that a server manifest declares a requested capability."""
        if requested_capability in manifest.capabilities:
            return True
        logger.warning(
            "Server '%s' attempted action requiring '%s' not in declared capabilities %s",
            manifest.name,
            requested_capability,
            manifest.capabilities,
        )
        return False

    @staticmethod
    def check_environment(
        manifest: ServerManifest, current_env: dict[str, str]
    ) -> tuple[bool, list[str]]:
        """Verify that all required environment variables for a server are present.

        Returns:
            Tuple of (ok, missing_vars).
        """
        missing = [
            var for var in manifest.required_env_vars if not current_env.get(var)
        ]
        return (not missing), missing
