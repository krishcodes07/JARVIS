"""
Connector Manager — Central orchestrator for discovering, loading, and managing messaging bridges.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from jarvis.connectors.base import BaseConnector
from jarvis.connectors.discovery import discover_connector_classes
from jarvis.connectors.models import ConnectorStatus

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class ConnectorManager:
    """Orchestrates all messaging connectors (Telegram, Discord, etc.).

    Auto-discovers connectors from the filesystem, handles concurrent startup of
    enabled bridges, graceful shutdowns, and health reporting.
    """

    def __init__(self, config: JarvisConfig, engine: JarvisEngine) -> None:
        self.config = config
        self.engine = engine
        self._connectors: dict[str, BaseConnector] = {}

        self._register_discovered_connectors()

    def _register_discovered_connectors(self) -> None:
        """Instantiate and register every connector found on disk.

        Connectors are discovered rather than listed, so adding a package under
        ``jarvis/connectors/`` or ``~/.jarvis/connectors/`` is enough to make it
        available. One broken connector never prevents the others from loading.
        """
        classes = discover_connector_classes()
        if not classes:
            logger.warning("No messaging connectors were discovered.")
            return

        for name, cls in classes.items():
            try:
                self.register(cls(self.config, self.engine))
            except Exception as e:
                logger.error(
                    "Failed to instantiate connector '%s' (%s): %s",
                    name,
                    cls.__name__,
                    e,
                    exc_info=True,
                )

        logger.info(
            "Registered %d connector(s): %s",
            len(self._connectors),
            ", ".join(sorted(self._connectors)) or "none",
        )

    def register(self, connector: BaseConnector) -> None:
        """Register a connector instance."""
        self._connectors[connector.name.lower()] = connector
        logger.debug(f"Registered connector: {connector.name}")

    def get(self, name: str) -> BaseConnector | None:
        """Get a connector by name."""
        return self._connectors.get(name.lower())

    def list_connectors(self) -> list[BaseConnector]:
        """List all registered connectors."""
        return list(self._connectors.values())

    def list_enabled(self) -> list[BaseConnector]:
        """List only connectors that are enabled in configuration."""
        if not self.config or not hasattr(self.config, "connectors") or not self.config.connectors.enabled:
            return []
        return [c for c in self._connectors.values() if c.is_enabled]

    def list_running(self) -> list[BaseConnector]:
        """List all currently active connectors."""
        return [c for c in self._connectors.values() if c.is_running]

    async def start_all(self) -> list[str]:
        """Start all connectors that are enabled in configuration.

        Returns:
            List of connector names that were successfully started.
        """
        if not self.config or not hasattr(self.config, "connectors") or not self.config.connectors.enabled:
            logger.info("Connectors subsystem is globally disabled in configuration.")
            return []

        enabled = self.list_enabled()
        if not enabled:
            logger.info("No messaging connectors are enabled in configuration.")
            return []

        started: list[str] = []
        tasks = []

        for conn in enabled:
            logger.info(f"Starting enabled connector '{conn.name}'...")
            tasks.append(self._safe_start(conn, started))

        if tasks:
            await asyncio.gather(*tasks)

        logger.info(f"Started {len(started)} connector(s): {', '.join(started) if started else 'none'}")
        return started

    async def _safe_start(self, connector: BaseConnector, started_collector: list[str]) -> None:
        """Safely start an individual connector, capturing any startup exceptions."""
        try:
            await connector.start()
            started_collector.append(connector.name)
        except Exception as e:
            logger.error(f"Failed to start connector '{connector.name}': {e}", exc_info=True)

    async def stop_all(self) -> None:
        """Stop all currently running connectors gracefully."""
        running = self.list_running()
        if not running:
            return

        logger.info(f"Stopping {len(running)} running connector(s)...")
        tasks = [conn.stop() for conn in running]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All connectors stopped.")

    async def start_connector(self, name: str) -> bool:
        """Start a specific connector by name."""
        connector = self.get(name)
        if not connector:
            raise ValueError(f"Connector '{name}' is not registered.")
        if connector.is_running:
            return True
        await connector.start()
        return True

    async def stop_connector(self, name: str) -> bool:
        """Stop a specific connector by name."""
        connector = self.get(name)
        if not connector:
            raise ValueError(f"Connector '{name}' is not registered.")
        if not connector.is_running:
            return True
        await connector.stop()
        return True

    def get_statuses(self) -> list[ConnectorStatus]:
        """Get status snapshots for all registered connectors."""
        return [c.get_status() for c in self._connectors.values()]
