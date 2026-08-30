"""
JARVIS System API — Endpoints for health inspection, memory management, and system status.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from jarvis import __version__
from jarvis.api.deps import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Inspect status of JARVIS Engine and subsystems."""
    engine = get_engine()
    is_init = bool(engine and engine._initialized)
    model = engine.last_used_model if engine else "JARVIS"

    connector_statuses = (
        [s.model_dump() for s in engine.connector_manager.get_statuses()]
        if (engine and engine.connector_manager)
        else []
    )

    return {
        "status": "healthy" if is_init else "degraded",
        "engine_initialized": is_init,
        "active_model": model,
        "connectors": connector_statuses,
        "version": __version__,
        # Which optional subsystems actually came up, so the UI can report the
        # truth instead of assuming everything is wired.
        "subsystems": {
            "voice": bool(engine and engine.voice_manager),
            "memory": bool(engine and engine.memory_manager),
            "vector_memory": bool(
                engine and engine.memory_manager and engine.memory_manager.vector
            ),
            "tools": bool(engine and engine.tool_registry),
            "mcp": bool(engine and getattr(engine, "mcp_manager", None)),
        },
    }


@router.post("/memory/clear")
async def clear_memory() -> dict[str, str]:
    """Clear vector embeddings memory store."""
    engine = get_engine()
    if engine and engine.memory_manager and engine.memory_manager.vector:
        try:
            await engine.memory_manager.vector.clear()
            return {"status": "success", "message": "Vector store memory cleared."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "noop", "message": "Vector store not initialized."}
