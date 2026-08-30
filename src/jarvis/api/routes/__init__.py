"""
JARVIS API Routes Registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from jarvis.api.routes.chat import router as chat_router
from jarvis.api.routes.config import router as config_router
from jarvis.api.routes.connectors import router as connectors_router
from jarvis.api.routes.mcp import router as mcp_router
from jarvis.api.routes.sessions import router as sessions_router
from jarvis.api.routes.skills import router as skills_router
from jarvis.api.routes.system import router as system_router
from jarvis.api.routes.tools import router as tools_router
from jarvis.api.routes.voice import router as voice_router

api_router = APIRouter(prefix="/api")

api_router.include_router(chat_router)
api_router.include_router(sessions_router)
api_router.include_router(config_router)
api_router.include_router(skills_router)
api_router.include_router(mcp_router)
api_router.include_router(connectors_router)
api_router.include_router(voice_router)
api_router.include_router(tools_router)
api_router.include_router(system_router)

__all__ = [
    "api_router",
    "chat_router",
    "config_router",
    "connectors_router",
    "mcp_router",
    "sessions_router",
    "skills_router",
    "system_router",
    "tools_router",
    "voice_router",
]
