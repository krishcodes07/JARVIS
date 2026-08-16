"""
Connector Runner — Standalone runner for launching JARVIS messaging bridges as background/foreground services.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


async def run_connector_service(
    config: JarvisConfig,
    connector_name: str | None = None,
) -> None:
    """Run JARVIS connector bridges in standalone service mode.

    Args:
        config: Full JarvisConfig instance.
        connector_name: Specific connector to run ('telegram', 'discord', or 'all'/None).
    """
    from jarvis.connectors.manager import ConnectorManager
    from jarvis.core.engine import JarvisEngine

    logger.info("Initializing JARVIS Engine for Connector Service...")
    engine = JarvisEngine()
    await engine.initialize(config)

    manager = engine.connector_manager
    if manager is None:
        from jarvis.connectors.manager import ConnectorManager
        manager = ConnectorManager(config, engine)
        engine.connector_manager = manager

    stop_event = asyncio.Event()

    # Handle OS termination signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Signal handlers not fully supported on Windows event loops
            pass

    try:
        if connector_name and connector_name.lower() not in ("all", "auto"):
            target = connector_name.lower()
            conn = manager.get(target)
            if conn and not conn.is_running:
                logger.info(f"Launching target connector '{target}'...")
                await manager.start_connector(target)
            elif conn and conn.is_running:
                logger.info(f"Connector '{target}' is already running.")

        running_connectors = manager.list_running()
        if not running_connectors:
            logger.warning(
                "No connectors are currently running. Check that connectors are enabled in jarvis.yaml "
                "or specify a connector via CLI: python -m jarvis --connector telegram"
            )
        else:
            names = ", ".join(c.name for c in running_connectors)
            logger.info(f"Active connectors: {names}")

        logger.info("JARVIS Connector Service is active. Press Ctrl+C to terminate.")
        await stop_event.wait()

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Shutting down Connector Service...")
        await engine.shutdown()
        logger.info("Connector Service stopped.")
