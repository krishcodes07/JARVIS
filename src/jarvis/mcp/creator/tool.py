"""
MCP Creator Tool Engine — Dynamically registers and configures MCP servers in JARVIS.

Allows JARVIS to install, configure, persist, and connect new MCP servers at runtime.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.mcp.registry import MCPRegistry

logger = logging.getLogger(__name__)


async def add_mcp_server(
    name: str,
    command: str,
    args: list[str] | None = None,
    transport: str = "stdio",
    description: str = "",
    env: dict[str, str] | None = None,
    url: str | None = None,
    auto_connect: bool = True,
    engine: Any | None = None,
) -> dict[str, Any]:
    """Dynamically register a new MCP server in JARVIS and persist to user config.

    Args:
        name: Unique identifier for the MCP server (e.g. 'postgres', 'github').
        command: Executable command (e.g. 'npx', 'uvx', 'python', 'node').
        args: Command-line arguments.
        transport: Communication transport ('stdio', 'sse', 'streamable_http').
        description: Description of the tools and capabilities.
        env: Optional environment variables or API keys.
        url: Optional endpoint URL for remote HTTP/SSE transports.
        auto_connect: Whether to immediately connect and verify. Defaults to True.
        engine: Optional JarvisEngine instance for live connection.

    Returns:
        Dictionary containing registration details, connection status, and tool counts.
    """
    clean_name = name.strip().lower().replace("-", "_")
    if not clean_name:
        raise ValueError("Server name cannot be empty.")

    registry = MCPRegistry()
    registry.load()

    server_config: dict[str, Any] = {
        "command": command.strip(),
        "args": list(args or []),
        "transport": transport.strip().lower(),
        "description": description.strip() or f"Dynamic MCP server: {clean_name}",
        "enabled": bool(auto_connect),
        "env": dict(env or {}),
    }
    if url:
        server_config["url"] = url.strip()

    # Register and persist to ~/.jarvis/mcp/servers.json
    registry.register(clean_name, server_config)
    registry.save_user_config()
    logger.info("Registered MCP server '%s' in user registry", clean_name)

    result: dict[str, Any] = {
        "success": True,
        "name": clean_name,
        "config": server_config,
        "connected": False,
        "tools_count": 0,
        "message": f"MCP server '{clean_name}' saved to ~/.jarvis/mcp/servers.json.",
    }

    # Attempt runtime connection if engine is available
    if auto_connect:
        if engine is None:
            try:
                from jarvis.core.engine import get_active_engine
                engine = get_active_engine()
            except Exception:
                engine = None

        mgr = getattr(engine, "mcp_manager", None) if engine else None
        if mgr:
            try:
                # Reload manager registry to pick up newly added server
                mgr.registry.load()
                ok, conn_msg = await mgr.connect_server(clean_name)
                if ok:
                    conn = mgr.client.connections.get(clean_name)
                    tools = list(conn.tools) if conn else []
                    tools_count = len(tools)
                    tool_names = [getattr(t, "name", str(t)) for t in tools]
                    result["connected"] = True
                    result["tools_count"] = tools_count
                    tool_list_str = f": {', '.join(tool_names)}" if tool_names else ""
                    result["message"] = (
                        f"✅ MCP server '{clean_name}' connected live in real time! "
                        f"Discovered {tools_count} new tools{tool_list_str}."
                    )
                else:
                    result["message"] = (
                        f"⚠️ MCP server '{clean_name}' saved, but live connection failed: {conn_msg}"
                    )
            except Exception as e:
                logger.warning("Error auto-connecting MCP server '%s': %s", clean_name, e)
                result["message"] = (
                    f"⚠️ MCP server '{clean_name}' saved, but live connection error: {e}"
                )

    return result
