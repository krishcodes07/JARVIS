"""
JARVIS Core API Layer — Reusable REST & WebSocket endpoints for all JARVIS clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jarvis.api.deps import set_engine
from jarvis.api.routes import api_router

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine


def create_api_app(engine: JarvisEngine | None = None) -> FastAPI:
    """Create and configure FastAPI application with all JARVIS API routes.

    Args:
        engine: Optional initialized JarvisEngine instance.

    Returns:
        Configured FastAPI application.
    """
    if engine is not None:
        set_engine(engine)

    app = FastAPI(
        title="JARVIS API",
        description="Just A Rather Very Intelligent System — Core Intelligence & Automation API",
        version="0.2.0",
    )

    # Enable CORS for local development and web frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


__all__ = ["create_api_app", "set_engine", "api_router"]
