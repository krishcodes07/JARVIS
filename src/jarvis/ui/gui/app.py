"""
GUI App — Desktop GUI for JARVIS.

Built with CustomTkinter for a modern desktop experience.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


async def run_gui(config: JarvisConfig) -> None:
    """Launch the JARVIS Desktop GUI.

    Args:
        config: JARVIS configuration.
    """
    # TODO: Implement using CustomTkinter
    logger.info("JARVIS GUI — not yet implemented.")
    print("JARVIS Desktop GUI is under development.")
    print("Please use --ui tui or --ui web instead.")
