"""
JARVIS Connectors API — Endpoints for managing Telegram, Discord, and messaging bridge connectors.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConnectorUpdateRequest(BaseModel):
    enabled: bool = Field(..., description="Target enabled status")
    bot_token: str | None = Field(default=None, description="Bot token")
    allowed_users: list[str] | None = Field(default=None, description="Allowed user identifiers")
    allowed_guilds: list[str] | None = Field(default=None, description="Allowed guild/group IDs (Discord)")


@router.get("")
async def list_connectors() -> list[dict[str, Any]]:
    """List all registered messaging connectors and their runtime status."""
    engine = get_engine()
    results: list[dict[str, Any]] = []

    if not engine:
        return results

    if engine.connector_manager:
        statuses = engine.connector_manager.get_statuses()
        for s in statuses:
            results.append({
                "name": s.name,
                "status": s.status,
                "error": s.error,
                "uptime": s.uptime,
                "messages_received": s.messages_received,
                "messages_sent": s.messages_sent,
            })
    else:
        # Fallback to reading config
        c = engine.config.connectors if (engine.config and hasattr(engine.config, "connectors")) else None
        if c:
            results.append({
                "name": "telegram",
                "status": "ready" if getattr(c.telegram, "enabled", False) else "disabled",
                "error": None,
                "uptime": 0,
                "messages_received": 0,
                "messages_sent": 0,
            })
            results.append({
                "name": "discord",
                "status": "ready" if getattr(c.discord, "enabled", False) else "disabled",
                "error": None,
                "uptime": 0,
                "messages_received": 0,
                "messages_sent": 0,
            })

    return results


@router.post("/{name}/configure")
async def configure_connector(name: str, request: ConnectorUpdateRequest) -> dict[str, Any]:
    """Update credentials and enabled state for a connector."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    conn_cfg = getattr(engine.config.connectors, name.lower(), None)
    if conn_cfg is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{name}'")

    conn_cfg.enabled = request.enabled
    if request.bot_token:
        conn_cfg.bot_token = request.bot_token
    if request.allowed_users is not None:
        conn_cfg.allowed_users = request.allowed_users
    if request.allowed_guilds is not None and hasattr(conn_cfg, "allowed_guilds"):
        conn_cfg.allowed_guilds = request.allowed_guilds

    engine.config.save()

    return {
        "status": "success",
        "name": name,
        "enabled": conn_cfg.enabled,
        "message": f"Connector '{name}' updated successfully.",
    }
