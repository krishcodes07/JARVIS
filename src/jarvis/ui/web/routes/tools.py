"""
Web UI Tools Routes — API endpoints for listing tools.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tools"])

_engine: JarvisEngine | None = None


def set_engine(engine: JarvisEngine | None) -> None:
    """Set the active JarvisEngine instance for this router module."""
    global _engine
    _engine = engine


def _get_engine() -> JarvisEngine | None:
    """Get the active JarvisEngine instance."""
    return _engine


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    """List all registered tools."""
    engine = _get_engine()
    if not engine or not engine.tool_registry:
        return []

    return [
        {
            "name": t.name,
            "description": t.description,
            "category": t.schema.category,
            "dangerous": t.schema.dangerous,
            "parameters": [p.model_dump() for p in t.schema.parameters],
        }
        for t in engine.tool_registry.list_tools()
    ]
