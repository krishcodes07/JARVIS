"""
JARVIS Config API — Endpoints for managing configuration, providers, models, reasoning effort, and API keys.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from jarvis.api.deps import get_engine
from jarvis.providers.models_dev import (
    format_env_var_label,
    get_model_effort_values,
    get_model_info,
    get_provider_env_vars,
    has_configurable_reasoning,
    is_provider_connected,
    load_models_dev_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


class ProviderSwitchRequest(BaseModel):
    provider: str = Field(..., description="Provider identifier (e.g. openai, anthropic, google)")
    model: str | None = Field(default=None, description="Model identifier")
    reasoning_effort: str | None = Field(default=None, description="Reasoning effort level")


class ProviderConnectRequest(BaseModel):
    provider: str = Field(..., description="Provider identifier")
    api_key: str | None = Field(default=None, description="API Key (legacy fallback)")
    base_url: str | None = Field(default=None, description="Custom base URL")
    keys: dict[str, str] | None = Field(default=None, description="Map of environment variable names to values")


class EffortRequest(BaseModel):
    effort: str = Field(..., description="Reasoning effort (none, low, medium, high, max)")


class ConfigUpdateRequest(BaseModel):
    jarvis: dict[str, Any] | None = None
    provider: dict[str, Any] | None = None
    ui: dict[str, Any] | None = None
    memory: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None
    voice: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None
    connectors: dict[str, Any] | None = None
    mcp: dict[str, Any] | None = None
    automation: dict[str, Any] | None = None


def _coerce_leaf(model: BaseModel, key: str, value: Any) -> Any:
    """Validate a leaf value against its declared field type."""
    field = type(model).model_fields.get(key)
    if field is None or field.annotation is None:
        # Model allows extras (e.g. MCPServerOverride) — pass through as-is.
        return value
    return TypeAdapter(field.annotation).validate_python(value)


def _merge_mapping(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge a patch into a plain-dict config field without dropping siblings."""
    merged: dict[str, Any] = {
        k: (v.model_dump() if isinstance(v, BaseModel) else v) for k, v in current.items()
    }
    for k, v in patch.items():
        existing = merged.get(k)
        if isinstance(v, dict) and isinstance(existing, dict):
            merged[k] = {**existing, **v}
        else:
            merged[k] = v
    return merged


def deep_merge_model(model: BaseModel, patch: dict[str, Any]) -> list[str]:
    """Recursively apply a nested dict patch onto a pydantic model, in place.

    Descending into nested models is what keeps a patch like
    ``{"voice": {"tts": {"voice": "x"}}}`` from replacing the whole ``tts``
    section with a raw dict and losing every sibling key.

    Returns:
        Dotted paths that could not be applied (unknown key or failed validation).
    """
    rejected: list[str] = []
    fields = type(model).model_fields

    for key, value in patch.items():
        if key not in fields and not hasattr(model, key):
            rejected.append(key)
            continue

        current = getattr(model, key, None)

        if isinstance(current, BaseModel) and isinstance(value, dict):
            rejected.extend(f"{key}.{sub}" for sub in deep_merge_model(current, value))
            continue

        if isinstance(current, dict) and isinstance(value, dict):
            value = _merge_mapping(current, value)

        try:
            setattr(model, key, _coerce_leaf(model, key, value))
        except (ValidationError, ValueError, TypeError) as e:
            logger.debug(f"Rejected config key {key!r}: {e}")
            rejected.append(key)

    return rejected


def _serialize_config(c: Any) -> dict[str, Any]:
    """Build the client-facing config payload."""
    user_name = getattr(c.jarvis, "user_name", getattr(c.jarvis, "user", "Sir")) or "Sir"
    return {
        "jarvis": {**c.jarvis.model_dump(), "user_name": user_name},
        "user_name": user_name,
        "provider": c.provider.model_dump(),
        "ui": c.ui.model_dump() if getattr(c, "ui", None) else {},
        "memory": c.memory.model_dump(),
        "tools": c.tools.model_dump(),
        "skills": c.skills.model_dump() if getattr(c, "skills", None) else {},
        "voice": c.voice.model_dump() if getattr(c, "voice", None) else {},
        "connectors": c.connectors.model_dump() if getattr(c, "connectors", None) else {},
        "mcp": c.mcp.model_dump() if getattr(c, "mcp", None) else {},
        "automation": c.automation.model_dump() if getattr(c, "automation", None) else {},
    }


@router.get("")
async def get_config() -> dict[str, Any]:
    """Get complete active JARVIS configuration."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    return _serialize_config(engine.config)


@router.patch("")
async def update_config(request: ConfigUpdateRequest) -> dict[str, Any]:
    """Deep-merge and persist configuration sections."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    cfg = engine.config
    patch = request.model_dump(exclude_none=True)

    rejected = deep_merge_model(cfg, patch)

    try:
        cfg.save()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {e}")

    voice_reloaded: bool | None = None
    if "voice" in patch:
        voice_reloaded = await _reload_voice(engine)

    return {
        "status": "success",
        "message": "Configuration updated successfully.",
        "rejected": rejected,
        "voice_reloaded": voice_reloaded,
        "config": _serialize_config(cfg),
    }


async def _reload_voice(engine: Any) -> bool | None:
    """Rebuild the voice subsystem after a ``voice`` patch, best-effort.

    A provider/enabled change is otherwise invisible until restart. Returns None
    when the engine cannot reload (e.g. a test double without the hook).
    """
    reload = getattr(engine, "reload_voice", None)
    if not callable(reload):
        return None
    try:
        result = reload()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    except Exception as e:
        logger.warning(f"Voice reload after config change failed: {e}")
        return False


@router.get("/providers")
async def list_providers() -> list[dict[str, Any]]:
    """List all providers from models.dev catalog with connection status."""
    engine = get_engine()
    cache = load_models_dev_cache()
    
    active_prov = engine.config.provider.active if (engine and engine.config) else "openai"
    active_model = engine.config.provider.model if (engine and engine.config) else ""

    results: list[dict[str, Any]] = []

    if cache:
        for pid, pdata in cache.items():
            if not isinstance(pdata, dict):
                continue
            connected = is_provider_connected(pid)
            models = pdata.get("models", [])
            model_count = len(models) if isinstance(models, (list, dict)) else 0
            raw_env_vars = get_provider_env_vars(pid, pdata)
            fields = [
                {
                    "name": ev,
                    "label": format_env_var_label(ev),
                    "is_secret": any(k in ev.upper() for k in ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH")),
                    "is_set": bool(os.getenv(ev)),
                }
                for ev in raw_env_vars
            ]
            results.append({
                "id": pid,
                "name": pdata.get("name") or pid.title(),
                "connected": connected,
                "is_active": (pid == active_prov),
                "model_count": model_count,
                "active_model": active_model if pid == active_prov else "",
                "doc_url": pdata.get("doc_url", ""),
                "env_vars": raw_env_vars,
                "fields": fields,
            })
    else:
        if engine and engine.provider_manager:
            for p in engine.provider_manager.registry.list_providers():
                connected = is_provider_connected(p.name)
                raw_env_vars = get_provider_env_vars(p.name)
                fields = [
                    {
                        "name": ev,
                        "label": format_env_var_label(ev),
                        "is_secret": any(k in ev.upper() for k in ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH")),
                        "is_set": bool(os.getenv(ev)),
                    }
                    for ev in raw_env_vars
                ]
                results.append({
                    "id": p.name,
                    "name": p.display_name or p.name.title(),
                    "connected": connected,
                    "is_active": (p.name == active_prov),
                    "model_count": 1,
                    "active_model": active_model if p.name == active_prov else "",
                    "doc_url": "",
                    "env_vars": raw_env_vars,
                    "fields": fields,
                })

    # Sort so connected/active providers appear first
    results.sort(key=lambda p: (not p["is_active"], not p["connected"], p["name"].lower()))
    return results


@router.get("/models")
async def list_models(provider: str | None = None) -> list[dict[str, Any]]:
    """List all models for a provider with reasoning capabilities."""
    engine = get_engine()
    active_prov = provider or (engine.config.provider.active if (engine and engine.config) else "openai")
    
    cache = load_models_dev_cache()
    pdata = cache.get(active_prov, {}) if isinstance(cache, dict) else {}
    models_raw = pdata.get("models", []) if isinstance(pdata, dict) else []

    results: list[dict[str, Any]] = []
    current_model = engine.config.provider.model if (engine and engine.config) else ""

    if isinstance(models_raw, dict):
        for mid, mdata in models_raw.items():
            if not isinstance(mdata, dict):
                mdata = {}
            mname = mdata.get("name") or mid
            efforts = get_model_effort_values(mid, active_prov)
            has_reasoning = bool(efforts) or has_configurable_reasoning(mid, active_prov)

            results.append({
                "id": str(mid),
                "name": str(mname),
                "provider": active_prov,
                "description": mdata.get("description", ""),
                "context_window": mdata.get("context_length") or mdata.get("context_window", 0),
                "max_tokens": mdata.get("max_tokens") or mdata.get("max_output_tokens", 0),
                "has_reasoning": has_reasoning,
                "available_efforts": efforts,
                "is_active": (str(mid) == current_model),
            })
    elif isinstance(models_raw, list):
        for m in models_raw:
            if isinstance(m, dict):
                mid = m.get("id") or m.get("name", "")
                mname = m.get("name") or mid
                desc = m.get("description", "")
                ctx = m.get("context_length") or m.get("context_window", 0)
                maxt = m.get("max_tokens") or m.get("max_output_tokens", 0)
            else:
                mid = str(m)
                mname = str(m)
                desc = ""
                ctx = 0
                maxt = 0

            efforts = get_model_effort_values(mid, active_prov)
            has_reasoning = bool(efforts) or has_configurable_reasoning(mid, active_prov)

            results.append({
                "id": str(mid),
                "name": str(mname),
                "provider": active_prov,
                "description": desc,
                "context_window": ctx,
                "max_tokens": maxt,
                "has_reasoning": has_reasoning,
                "available_efforts": efforts,
                "is_active": (str(mid) == current_model),
            })

    # If no models found in cache for this provider, fallback to current model
    if not results and current_model:
        results.append({
            "id": current_model,
            "name": current_model,
            "provider": active_prov,
            "description": "Active model",
            "context_window": 0,
            "max_tokens": 0,
            "has_reasoning": False,
            "available_efforts": [],
            "is_active": True,
        })

    return results


@router.post("/provider/switch")
async def switch_provider(request: ProviderSwitchRequest) -> dict[str, Any]:
    """Switch active LLM provider and model."""
    engine = get_engine()
    if not engine or not engine.provider_manager:
        raise HTTPException(status_code=500, detail="Provider manager unavailable.")

    try:
        await engine.provider_manager.switch_provider(request.provider)
        if engine.config:
            engine.config.provider.active = request.provider
            if request.model:
                engine.config.provider.model = request.model
            if request.reasoning_effort is not None:
                if request.reasoning_effort.lower() in ("none", "off", "0"):
                    engine.config.provider.thinking = False
                    engine.config.provider.reasoning_effort = "none"
                else:
                    engine.config.provider.thinking = True
                    engine.config.provider.reasoning_effort = request.reasoning_effort.lower()
            engine.config.save()

        return {
            "status": "success",
            "provider": request.provider,
            "model": engine.config.provider.model if engine.config else request.model,
            "reasoning_effort": engine.config.provider.reasoning_effort if engine.config else "none",
            "message": f"Successfully switched to {request.provider}.",
        }
    except Exception as e:
        logger.exception("Failed switching provider")
        raise HTTPException(status_code=500, detail=f"Provider switch failed: {e}")


@router.post("/provider/connect")
async def connect_provider(request: ProviderConnectRequest) -> dict[str, Any]:
    """Save API key(s) / credentials for a provider and attempt connection."""
    from jarvis.core.config import save_api_key_to_env
    from jarvis.providers.models_dev import get_provider_env_vars

    saved_vars: list[str] = []

    # 1. Save all keys provided in the dictionary
    if request.keys:
        for var_name, var_value in request.keys.items():
            val = var_value.strip() if var_value is not None else ""
            if val:
                save_api_key_to_env(var_name, val)
                saved_vars.append(var_name)

    # 2. Fallback to single api_key if provided
    if request.api_key and not saved_vars:
        env_vars = get_provider_env_vars(request.provider)
        env_var = env_vars[0] if env_vars else f"{request.provider.upper()}_API_KEY"
        save_api_key_to_env(env_var, request.api_key.strip())
        saved_vars.append(env_var)

    engine = get_engine()
    if engine and engine.config:
        if request.base_url:
            if not hasattr(engine.config.provider, "base_urls") or engine.config.provider.base_urls is None:
                engine.config.provider.base_urls = {}
            engine.config.provider.base_urls[request.provider] = request.base_url
        engine.config.save()

    connected = is_provider_connected(request.provider)
    msg = (
        f"Saved {', '.join(saved_vars)} in ~/.jarvis/.env"
        if saved_vars
        else f"Credentials saved for {request.provider}."
    )

    return {
        "status": "success",
        "provider": request.provider,
        "env_var": saved_vars[0] if saved_vars else "",
        "env_vars": saved_vars,
        "connected": connected,
        "message": msg,
    }


@router.get("/effort")
async def get_effort_info() -> dict[str, Any]:
    """Get reasoning effort availability for the currently active model."""
    engine = get_engine()
    if not engine or not engine.config:
        return {"model": "", "supported": False, "available": [], "current": "none"}

    prov = engine.config.provider.active
    model = engine.config.provider.model
    current = engine.config.provider.reasoning_effort or "none"

    efforts = get_model_effort_values(model, prov)
    supported = bool(efforts) or has_configurable_reasoning(model, prov)

    return {
        "model": model,
        "provider": prov,
        "supported": supported,
        "available": efforts if efforts else (["none", "low", "medium", "high", "max"] if supported else []),
        "current": current,
    }


@router.post("/effort")
async def set_effort(request: EffortRequest) -> dict[str, Any]:
    """Set the reasoning effort for the current model."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    effort = request.effort.lower().strip()
    if effort in ("none", "off", "0"):
        engine.config.provider.thinking = False
        engine.config.provider.reasoning_effort = "none"
    else:
        engine.config.provider.thinking = True
        engine.config.provider.reasoning_effort = effort

    try:
        engine.config.save()
        return {
            "status": "success",
            "model": engine.config.provider.model,
            "reasoning_effort": engine.config.provider.reasoning_effort,
            "thinking": engine.config.provider.thinking,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save effort setting: {e}")
