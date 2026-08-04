"""
Universal server runner for MCP server packages.

Dynamically constructs a FastMCP server instance from a package's
``tools/``, ``resources/``, and ``prompts/`` folders.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from jarvis.mcp.platform.loader import ServerPackageLoader

logger = logging.getLogger(__name__)


def create_server_from_package(server_file_path: str) -> FastMCP:
    """Construct a FastMCP server by discovering a package's components.

    Args:
        server_file_path: Usually ``__file__`` of the server package's ``server.py``.

    Returns:
        A fully configured :class:`FastMCP` server instance.
    """
    server_dir = Path(server_file_path).parent.resolve()
    loader = ServerPackageLoader(server_dir)

    manifest = loader.manifest
    logger.info("Building FastMCP server '%s' from %s", manifest.name, server_dir)

    mcp = FastMCP(
        name=manifest.name,
        instructions=manifest.description or f"MCP Server '{manifest.name}'",
    )

    # 1. Register discovered tools
    for t in loader.discover_tools():
        if t.func:
            try:
                mcp.add_tool(t.func, name=t.name, description=t.description)
                logger.debug("Added tool '%s' to FastMCP '%s'", t.name, manifest.name)
            except Exception as e:
                logger.error("Failed to add tool '%s': %s", t.name, e)

    # 2. Register discovered resources
    for r in loader.discover_resources():
        if r.func:
            try:
                mcp.resource(
                    r.uri, name=r.name, description=r.description, mime_type=r.mime_type
                )(r.func)
                logger.debug("Added resource '%s' to FastMCP '%s'", r.uri, manifest.name)
            except Exception as e:
                logger.error("Failed to add resource '%s': %s", r.uri, e)

    # 3. Register discovered prompts
    for p in loader.discover_prompts():
        try:
            if p.func:
                mcp.prompt(name=p.name, description=p.description)(p.func)
            elif p.template:
                mcp.prompt(name=p.name, description=p.description)(
                    _make_template_handler(p.template)
                )
            logger.debug("Added prompt '%s' to FastMCP '%s'", p.name, manifest.name)
        except Exception as e:
            logger.error("Failed to add prompt '%s': %s", p.name, e)

    return mcp


def _make_template_handler(template: str):
    """Create a prompt handler that formats a template with keyword arguments."""

    def prompt_handler(**kwargs: Any) -> str:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

    return prompt_handler
