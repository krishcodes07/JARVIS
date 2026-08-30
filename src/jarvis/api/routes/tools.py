"""
JARVIS Tools API — Endpoints for listing registered system, desktop, filesystem, and basic tools.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from jarvis.api.deps import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools() -> list[dict[str, Any]]:
    """List all registered tools available to JARVIS."""
    engine = get_engine()
    if not engine or not engine.tool_registry:
        return []

    return [
        {
            "name": t.name,
            "description": t.description,
            "category": getattr(t.schema, "category", "general"),
            "dangerous": getattr(t.schema, "dangerous", False),
            "parameters": [
                p.model_dump() if hasattr(p, "model_dump") else dict(p)
                for p in getattr(t.schema, "parameters", [])
            ],
        }
        for t in engine.tool_registry.list_tools()
    ]
