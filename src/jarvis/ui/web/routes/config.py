"""
Web UI Config Routes — API endpoints for managing settings, providers, and models.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

_engine: JarvisEngine | None = None


def set_engine(engine: JarvisEngine | None) -> None:
    """Set the active JarvisEngine instance for this router module."""
    global _engine
    _engine = engine


def _get_engine() -> JarvisEngine | None:
    """Get the active JarvisEngine instance."""
    return _engine


class ProviderSwitchRequest(BaseModel):
    provider: str
    model: str | None = None


@router.get("/")
async def get_config() -> dict[str, Any]:
    """Get current configuration."""
    engine = _get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine config not loaded.")

    c = engine.config
    return {
        "jarvis": c.jarvis.model_dump(),
        "provider": c.provider.model_dump(),
        "memory": c.memory.model_dump(),
        "tools": c.tools.model_dump(),
        "mcp": c.mcp.model_dump(),
    }


@router.get("/providers")
async def list_providers() -> list[dict[str, Any]]:
    """List all available providers from providers.json."""
    engine = _get_engine()
    if not engine or not engine.provider_manager:
        raise HTTPException(status_code=500, detail="Provider manager unavailable.")

    definitions = engine.provider_manager.registry.list_providers()
    return [
        {
            "name": d.name,
            "display_name": d.display_name,
            "protocol": d.protocol,
            "default_model": d.default_model,
            "supports": d.supports,
        }
        for d in definitions
    ]


@router.get("/models")
async def list_models(provider: str | None = None) -> list[dict[str, Any]]:
    """Fetch live models for a provider dynamically from its API endpoint."""
    engine = _get_engine()
    if not engine or not engine.provider_manager:
        raise HTTPException(status_code=500, detail="Provider manager unavailable.")

    models: list[dict[str, Any]] = await engine.provider_manager.get_models(provider)
    return models


@router.post("/provider")
async def switch_provider(request: ProviderSwitchRequest) -> dict[str, str]:
    """Switch active provider and model."""
    engine = _get_engine()
    if not engine or not engine.provider_manager:
        raise HTTPException(status_code=500, detail="Provider manager unavailable.")

    try:
        await engine.provider_manager.switch_provider(request.provider)
        if engine.config:
            engine.config.provider.active = request.provider
            if request.model:
                engine.config.provider.model = request.model
            engine.config.save()
        return {
            "status": "success",
            "provider": request.provider,
            "model": engine.config.provider.model if engine.config else "",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
