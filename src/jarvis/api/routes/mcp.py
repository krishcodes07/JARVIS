"""
JARVIS MCP API — Endpoints for viewing, adding, connecting, and toggling Model Context Protocol servers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine
from jarvis.core.config import MCPServerOverride
from jarvis.mcp.auth.oauth import GoogleOAuthHelper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _as_override(value: Any) -> MCPServerOverride:
    """Normalise a config entry to an MCPServerOverride.

    ``config.mcp.servers`` is typed as ``dict[str, MCPServerOverride]``, but a
    YAML file written by an older build (or hand-edited) may still hold plain
    dicts. Coerce both shapes so callers can use attribute access safely.
    """
    if isinstance(value, MCPServerOverride):
        return value
    if isinstance(value, dict):
        try:
            return MCPServerOverride(**value)
        except Exception:
            return MCPServerOverride()
    return MCPServerOverride()


def _get_servers(engine: Any) -> dict[str, MCPServerOverride]:
    """Read the configured MCP servers as a normalised mapping.

    Also heals the in-memory config so a later ``cfg.save()`` serialises typed
    models rather than raw dicts (which pydantic cannot round-trip cleanly).
    """
    cfg_mcp = getattr(engine.config, "mcp", None) if getattr(engine, "config", None) else None
    servers = getattr(cfg_mcp, "servers", None)
    if not isinstance(servers, dict):
        return {}

    normalised = {name: _as_override(entry) for name, entry in servers.items()}
    if any(not isinstance(entry, MCPServerOverride) for entry in servers.values()):
        try:
            cfg_mcp.servers = dict(normalised)
        except Exception:
            pass
    return normalised


class AddMCPServerRequest(BaseModel):
    name: str = Field(..., description="Server identifier (e.g. filesystem, github)")
    command: str = Field(..., description="Command to execute (e.g. npx, python, node)")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    transport: str = Field(default="stdio", description="Transport type (stdio or sse)")
    url: str | None = Field(default=None, description="URL for SSE transport")


class ToggleMCPServerRequest(BaseModel):
    enabled: bool = Field(..., description="Target enabled state")


def _registry_entries(manager: Any) -> dict[str, dict[str, Any]]:
    """Read servers.json entries as a mapping, tolerating registry stubs."""
    try:
        entries = manager.registry.get_all()
    except Exception:
        return {}
    return entries if isinstance(entries, dict) else {}


def _resolve_enabled(
    override: MCPServerOverride | None,
    entry: dict[str, Any],
    manifest: Any | None,
) -> bool:
    """Decide whether a server counts as enabled.

    Mirrors :meth:`MCPManager._build_server_configs` so the settings toggle shows
    the same state the engine will act on at startup: an explicit config override
    wins, then servers.json, then the manifest's default.
    """
    if override is not None and override.enabled is not None:
        return bool(override.enabled)
    if "enabled" in entry:
        return bool(entry.get("enabled"))
    return bool(getattr(manifest, "enabled_by_default", False)) if manifest else False


def _write_override(engine: Any, name: str, enabled: bool) -> None:
    """Persist a server's enabled flag as a typed override, creating it if needed.

    The previous implementation only updated servers that already had an entry,
    so toggling a built-in (manifest-discovered) server silently did nothing.
    """
    cfg = getattr(engine, "config", None)
    if not cfg or not getattr(cfg, "mcp", None):
        return

    if not isinstance(getattr(cfg.mcp, "servers", None), dict):
        cfg.mcp.servers = {}

    existing = cfg.mcp.servers.get(name)
    override = _as_override(existing) if existing is not None else MCPServerOverride()
    override.enabled = enabled
    cfg.mcp.servers[name] = override

    try:
        cfg.save()
    except Exception as e:
        logger.warning(f"Could not persist MCP override for {name!r}: {e}")


@router.get("/servers")
async def list_mcp_servers() -> list[dict[str, Any]]:
    """List all configured MCP servers, connection status, tool count, and manifest metadata."""
    engine = get_engine()
    if not engine or not engine.mcp_manager:
        return []

    manager = engine.mcp_manager
    manifests = getattr(manager, "_manifests", {})
    registered_servers = manager.registry.list_servers()
    connections = getattr(manager.client, "connections", {})
    entries = _registry_entries(manager)

    registered_names = set()
    for s in registered_servers:
        if isinstance(s, str):
            registered_names.add(s)
        elif hasattr(s, "name"):
            registered_names.add(s.name)

    all_names = set(manifests.keys()).union(registered_names)

    # Also include any servers configured in user config
    user_servers = _get_servers(engine)
    all_names = all_names.union(user_servers.keys())

    results: list[dict[str, Any]] = []

    for name in sorted(all_names):
        conn = connections.get(name) if isinstance(connections, dict) else None
        # ServerConnection exposes `connected`; the old code read a non-existent
        # `is_connected`, so every server always reported as offline.
        is_connected = bool(getattr(conn, "connected", False)) if conn is not None else False
        tool_count = len(getattr(conn, "tools", []) or []) if is_connected else 0

        manifest = manifests.get(name)
        override = user_servers.get(name)
        entry = entries.get(name) if isinstance(entries.get(name), dict) else {}
        description = (override.description if override and override.description else None) or (
            manifest.description if manifest else ""
        )
        category = manifest.category if manifest else "custom"
        requires_oauth = bool(manifest and manifest.oauth)

        is_enabled = is_connected or _resolve_enabled(override, entry or {}, manifest)

        results.append({
            "name": name,
            "description": description,
            "category": category,
            "connected": is_connected,
            "enabled": is_enabled,
            "tool_count": tool_count,
            "requires_oauth": requires_oauth,
            "transport": (override.transport if override else None)
            or str(entry.get("transport") or "stdio"),
            "custom": name in user_servers and manifest is None,
        })

    return results


@router.post("/add")
async def add_mcp_server(request: AddMCPServerRequest) -> dict[str, Any]:
    """Add a new custom MCP server to configuration and attempt connection."""
    engine = get_engine()
    if not engine or not engine.config or not engine.mcp_manager:
        raise HTTPException(status_code=500, detail="Engine or MCP manager not available.")

    # Store as a typed override so cfg.save()'s model_dump() round-trips it.
    server_entry = MCPServerOverride(
        enabled=True,
        transport=request.transport,
        command=request.command,
        args=request.args,
        env=request.env,
        url=request.url,
    )

    # Save to user config
    if not isinstance(getattr(engine.config.mcp, "servers", None), dict):
        engine.config.mcp.servers = {}

    engine.config.mcp.servers[request.name] = server_entry
    engine.config.save()

    # Attempt runtime connection
    try:
        ok, msg = await engine.mcp_manager.connect_server(request.name)
        return {
            "status": "success" if ok else "warning",
            "name": request.name,
            "connected": ok,
            "message": msg,
        }
    except Exception as e:
        return {
            "status": "saved",
            "name": request.name,
            "connected": False,
            "message": str(e),
        }


@router.post("/{name}/toggle")
async def toggle_mcp_server(name: str, request: ToggleMCPServerRequest) -> dict[str, Any]:
    """Connect or disconnect an MCP server, persisting the choice.

    The enabled flag is written to ``config.mcp.servers`` in every case — including
    for manifest-discovered built-ins that had no override yet — so the state
    survives a restart and the settings toggle stops springing back.
    """
    engine = get_engine()
    if not engine or not engine.mcp_manager:
        raise HTTPException(status_code=500, detail="MCP Manager unavailable.")

    manager = engine.mcp_manager

    if request.enabled:
        try:
            ok, msg = await manager.connect_server(name)
        except Exception as e:
            logger.exception(f"Enabling MCP server {name!r} failed")
            raise HTTPException(status_code=500, detail=str(e))

        if ok:
            _write_override(engine, name, True)
        return {
            "status": "success" if ok else "error",
            "name": name,
            "connected": ok,
            "enabled": ok,
            "message": msg,
        }

    # Disabling must always succeed from the user's point of view: persist the
    # flag even if the process was never connected (or teardown misbehaves).
    message = f"Server '{name}' disabled."
    try:
        result = await _disconnect(manager, name)
        if result:
            message = result
    except Exception as e:
        logger.warning(f"Disconnect of MCP server {name!r} reported an error: {e}")
        message = f"Server '{name}' disabled (disconnect reported: {e})."

    _write_override(engine, name, False)
    return {
        "status": "success",
        "name": name,
        "connected": False,
        "enabled": False,
        "message": message,
    }


async def _disconnect(manager: Any, name: str) -> str | None:
    """Tear down a live connection, preferring the manager's own bookkeeping.

    ``MCPManager.disconnect_server`` also flips the flag in servers.json, which a
    bare ``client.disconnect`` would leave stale.
    """
    disconnect_server = getattr(manager, "disconnect_server", None)
    if callable(disconnect_server):
        outcome = await disconnect_server(name)
        if isinstance(outcome, tuple) and len(outcome) == 2:
            _, msg = outcome
            return str(msg)
        return None

    await manager.client.disconnect(name)
    return None


@router.delete("/{name}")
async def delete_mcp_server(name: str) -> dict[str, str]:
    """Remove a custom MCP server from configuration."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    if engine.mcp_manager and name in engine.mcp_manager.client.connections:
        try:
            await engine.mcp_manager.client.disconnect(name)
        except Exception:
            pass

    servers = getattr(engine.config.mcp, "servers", None)
    if isinstance(servers, dict) and name in servers:
        del servers[name]
        engine.config.save()

    return {"status": "deleted", "name": name}


@router.post("/auth/google")
async def google_oauth_login() -> dict[str, Any]:
    """Trigger Google OAuth login flow in user's browser."""
    try:
        res = await GoogleOAuthHelper.start_browser_login()
        email = res.get("email", "Google Account")
        return {"status": "success", "email": email, "message": f"Successfully authenticated as {email}"}
    except Exception as e:
        logger.exception("Google OAuth login failed")
        raise HTTPException(status_code=500, detail=f"OAuth login failed: {e}")
