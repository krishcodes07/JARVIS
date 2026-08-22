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
        connector_name: Specific connector to run (a discovered connector name,
            or 'all'/'auto'/None to run everything enabled in configuration).
    """
    from jarvis.connectors.manager import ConnectorManager
    from jarvis.core.engine import JarvisEngine

    logger.info("Initializing JARVIS Engine for Connector Service...")
    engine = JarvisEngine()
    await engine.initialize(config)

    manager = engine.connector_manager
    if manager is None:
        manager = ConnectorManager(config, engine)
        engine.connector_manager = manager

    stop_event = asyncio.Event()
    _install_stop_handlers(stop_event)

    try:
        if connector_name and connector_name.lower() not in ("all", "auto"):
            target = connector_name.lower()
            conn = manager.get(target)
            if conn is None:
                available = ", ".join(c.name for c in manager.list_connectors()) or "none"
                logger.error(
                    "Connector '%s' is not available. Discovered connectors: %s",
                    target,
                    available,
                )
            elif conn.is_running:
                logger.info(f"Connector '{target}' is already running.")
            else:
                logger.info(f"Launching target connector '{target}'...")
                await manager.start_connector(target)

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


def _install_stop_handlers(stop_event: asyncio.Event) -> None:
    """Wire SIGINT/SIGTERM to *stop_event* on whatever platform we're on.

    ``loop.add_signal_handler`` is unimplemented on Windows ProactorEventLoop, so
    fall back to :func:`signal.signal`, scheduling the set thread-safely since
    the handler runs outside the loop.
    """
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
            continue
        except (NotImplementedError, AttributeError, RuntimeError, ValueError):
            pass

        try:
            signal.signal(
                sig,
                lambda _sig, _frame: loop.call_soon_threadsafe(stop_event.set),
            )
        except (ValueError, OSError, RuntimeError) as e:
            # Not on the main thread, or the signal isn't supported here.
            logger.debug("Could not install handler for %s: %s", sig, e)
