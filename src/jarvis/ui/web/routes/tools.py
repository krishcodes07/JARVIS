"""
Web UI Tools Routes — API endpoints for listing tools.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    """List all registered tools."""
    engine = getattr(router, "engine", None)
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
