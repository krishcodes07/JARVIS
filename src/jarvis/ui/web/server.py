"""
Web UI Server — FastAPI-based web server for JARVIS.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jarvis.ui.web.routes import chat
from jarvis.ui.web.routes import config as config_router
from jarvis.ui.web.routes import tools as tools_router

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


async def run_web(config: JarvisConfig) -> None:
    """Launch the JARVIS Web UI.

    Args:
        config: JARVIS configuration.
    """
    import uvicorn

    from jarvis.core.engine import JarvisEngine

    # Initialize Engine
    engine = JarvisEngine()
    await engine.initialize(config)

    app = FastAPI(
        title="JARVIS",
        description="Just A Rather Very Intelligent System",
        version="0.1.0",
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.engine = engine

    # Pass engine instance to route modules
    chat.set_engine(engine)
    config_router.set_engine(engine)
    tools_router.set_engine(engine)

    # Include API routers
    app.include_router(chat.router)
    app.include_router(config_router.router)
    app.include_router(tools_router.router)

    # Setup static files and templates
    web_dir = Path(__file__).parent
    frontend_dir = web_dir / "frontend"
    static_dir = frontend_dir / "static"
    templates_dir = frontend_dir / "templates"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates = Jinja2Templates(directory=str(templates_dir)) if templates_dir.exists() else None

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Serve main web page."""
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        if templates and (templates_dir / "base.html").exists():
            return templates.TemplateResponse(request=request, name="base.html")
        return HTMLResponse(content="<h1>JARVIS Web UI</h1><p>Frontend static files missing.</p>")

    @app.get("/api/health")
    async def health():
        return {"status": "healthy", "version": "0.1.0", "engine": engine._initialized}

    @app.on_event("shutdown")
    async def shutdown_event():
        await engine.shutdown()

    host = config.ui.web.host
    port = config.ui.web.port
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    logger.info(f"Starting JARVIS Web UI at http://{display_host}:{port}")

    config_uvicorn = uvicorn.Config(
        app, host=host, port=port, log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()
