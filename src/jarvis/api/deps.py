"""
JARVIS API Dependencies & Shared State.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)

_engine: JarvisEngine | None = None


def set_engine(engine: JarvisEngine | None) -> None:
    """Set the active JarvisEngine instance for the API router."""
    global _engine
    _engine = engine


def get_engine() -> JarvisEngine | None:
    """Get the active JarvisEngine instance."""
    return _engine


def require_engine() -> JarvisEngine:
    """Get active engine or raise error if uninitialized."""
    if _engine is None or not _engine._initialized:
        raise RuntimeError("JARVIS Engine is not initialized.")
    return _engine
