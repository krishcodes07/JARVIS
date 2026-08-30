"""
JARVIS Web UI Server — FastAPI web application hosting the React Vite SPA and Core API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from jarvis.api import create_api_app
from jarvis.api.deps import set_engine

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


# Shown instead of the raw dev index.html (which references /src/main.tsx and
# 404s in production) when no built bundle is present.
_BUILD_INSTRUCTIONS = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>JARVIS — build required</title>
    <style>
        :root { color-scheme: dark; }
        body {
            margin: 0; min-height: 100vh; display: flex; align-items: center;
            justify-content: center; background: #07080f;
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
            color: #e5e7eb;
        }
        .card {
            max-width: 34rem; padding: 2.5rem; border-radius: 1.25rem;
            background: #0e1018; border: 1px solid rgba(139,92,246,0.25);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        h1 { margin: 0 0 .25rem; font-size: 1.35rem; color: #a78bfa; }
        p { margin: .5rem 0; line-height: 1.6; color: #9ca3af; font-size: .9rem; }
        code, pre {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: .82rem;
        }
        pre {
            margin: 1rem 0 .25rem; padding: .9rem 1rem; border-radius: .6rem;
            background: #05060b; border: 1px solid rgba(255,255,255,0.06);
            color: #c4b5fd; overflow-x: auto;
        }
        .hint { font-size: .78rem; color: #6b7280; }
    </style>
</head>
<body>
    <div class="card">
        <h1>JARVIS Web UI isn't built yet</h1>
        <p>The frontend bundle was not found. Build it once, then reload this page:</p>
        <pre>cd src/jarvis/ui/web/frontend
npm install
npm run build</pre>
        <p class="hint">During development you can instead run <code>npm run dev</code> in that
        folder and open <code>http://localhost:5173</code>, which proxies the API back here.</p>
    </div>
</body>
</html>
"""


def create_web_app(engine=None, dist_dir: Path | None = None):
    """Create FastAPI app with API routers and SPA static file mounting.

    Args:
        engine: Optional initialized JarvisEngine instance.
        dist_dir: Override for the built frontend directory. Defaults to
            ``frontend/dist`` next to this module; tests pass an explicit path to
            exercise both the built and unbuilt branches.
    """
    app = create_api_app(engine)

    if dist_dir is None:
        dist_dir = Path(__file__).parent / "frontend" / "dist"

    # If a built Vite bundle exists, mount its static assets and serve the SPA.
    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def serve_spa(request: Request, full_path: str):
            # Do not intercept API or WebSocket requests.
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                return HTMLResponse(status_code=404, content="Not found")

            # Serve a real static file from dist if the path points at one.
            candidate = dist_dir / full_path
            if full_path and candidate.exists() and candidate.is_file():
                return FileResponse(str(candidate))

            # Otherwise fall through to index.html for client-side routing.
            index_file = dist_dir / "index.html"
            if index_file.exists():
                return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
            return HTMLResponse(content=_BUILD_INSTRUCTIONS, status_code=503)
    else:
        # No build at all — every non-API route explains how to make one, rather
        # than serving the dev index.html that only works under Vite.
        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def build_required(request: Request, full_path: str):
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                return HTMLResponse(status_code=404, content="Not found")
            return HTMLResponse(content=_BUILD_INSTRUCTIONS, status_code=503)

    return app


async def run_web(
    config: JarvisConfig,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Launch the JARVIS Web UI server.

    Args:
        config: JARVIS configuration.
        host: Optional override for host address.
        port: Optional override for port number.
    """
    import uvicorn

    from jarvis.core.engine import JarvisEngine

    # Initialize the engine before wiring it into the API layer.
    engine = JarvisEngine()
    await engine.initialize(config)
    set_engine(engine)

    @asynccontextmanager
    async def lifespan(_app):
        # Startup already happened above; this owns the clean shutdown, replacing
        # the deprecated @app.on_event("shutdown") hook.
        try:
            yield
        finally:
            await engine.shutdown()

    app = create_web_app(engine)
    app.router.lifespan_context = lifespan

    host = host or (config.ui.web.host if hasattr(config.ui, "web") else "127.0.0.1")
    port = port or (config.ui.web.port if hasattr(config.ui, "web") else 8000)
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    logger.info(f"Starting JARVIS Web UI at http://{display_host}:{port}")

    config_uvicorn = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config_uvicorn)
    await server.serve()
