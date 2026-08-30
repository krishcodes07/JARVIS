"""
JARVIS Skills API — Endpoints for listing, creating, toggling, and inspecting modular skills.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine
from jarvis.core.exceptions import SkillLoadError, SkillNotFoundError
from jarvis.skills.manager import (
    create_skill,
    delete_skill,
    get_skill_readme,
    get_user_skills_directory,
    is_skill_disabled,
    list_available_skills,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


class ToggleSkillRequest(BaseModel):
    enabled: bool = Field(..., description="Whether skill should be enabled")


class CreateSkillRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Full README.md markdown body")
    name: str | None = Field(
        default=None, description="Optional skill name; derived from the content when omitted"
    )
    overwrite: bool = Field(
        default=False, description="Replace an existing skill with the same name"
    )


@router.get("")
async def list_skills() -> list[dict[str, Any]]:
    """List every skill, including disabled ones.

    Disabled skills used to be filtered out of this listing, which made switching
    one off remove it from the panel — leaving no way to switch it back on.
    """
    engine = get_engine()
    config = engine.config if engine else None

    available = list_available_skills(config=config, include_disabled=True)
    results: list[dict[str, Any]] = []

    for s in available:
        sname = s.get("name", "")
        results.append({
            "name": sname,
            "description": s.get("description", ""),
            "path": s.get("path", ""),
            "enabled": bool(s.get("enabled", not is_skill_disabled(sname, config=config))),
            "custom": bool(s.get("custom", False)),
        })

    return results


@router.post("", status_code=201)
async def add_skill(request: CreateSkillRequest) -> dict[str, Any]:
    """Create a skill from pasted README.md content.

    The skill is written to ``~/.jarvis/workspace/skills/<name>/README.md`` and is
    picked up by discovery immediately — no restart needed.
    """
    engine = get_engine()
    config = engine.config if engine else None

    try:
        created = create_skill(
            content=request.content,
            name=request.name,
            config=config,
            overwrite=request.overwrite,
        )
    except SkillLoadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Skill creation failed")
        raise HTTPException(status_code=500, detail=f"Could not create skill: {e}")

    return {
        "status": "success",
        "name": created["name"],
        "description": created["description"],
        "path": created["path"],
        "enabled": True,
        "custom": True,
        "message": f"Skill '{created['name']}' created.",
    }


@router.get("/directory")
async def get_skills_location() -> dict[str, str]:
    """Where user-created skills live, for the settings panel's hint text."""
    return {"path": str(get_user_skills_directory())}


@router.get("/{name}")
async def get_skill_detail(name: str) -> dict[str, Any]:
    """Get detailed markdown instruction content of a specific skill."""
    engine = get_engine()
    config = engine.config if engine else None

    try:
        # The panel previews disabled skills too, so read past the enabled check.
        content = get_skill_readme(name, config=config, include_disabled=True)
    except (SkillNotFoundError, SkillLoadError) as e:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found: {e}")
    except Exception as e:
        logger.exception(f"Could not read skill {name!r}")
        raise HTTPException(status_code=500, detail=f"Could not read skill '{name}': {e}")

    return {
        "name": name,
        "content": content,
        "enabled": not is_skill_disabled(name, config=config),
    }


@router.delete("/{name}")
async def remove_skill(name: str) -> dict[str, str]:
    """Delete a user-created skill. Built-in skills can only be disabled."""
    engine = get_engine()
    config = engine.config if engine else None

    try:
        removed = delete_skill(name, config=config)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SkillLoadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Could not delete skill {name!r}")
        raise HTTPException(status_code=500, detail=f"Could not delete skill '{name}': {e}")

    return {"status": "deleted", "name": removed}


@router.post("/{name}/toggle")
async def toggle_skill(name: str, request: ToggleSkillRequest) -> dict[str, Any]:
    """Enable or disable a specific skill."""
    engine = get_engine()
    if not engine or not engine.config:
        raise HTTPException(status_code=500, detail="Engine configuration not loaded.")

    cfg = engine.config
    disabled_list = list(getattr(cfg.skills, "disabled_skills", []) or [])
    norm_name = name.strip().lower().replace("_", "-")

    if request.enabled:
        # Remove from disabled_skills
        disabled_list = [s for s in disabled_list if s.strip().lower().replace("_", "-") != norm_name]
        # A per-skill enable is meaningless while the subsystem master switch is
        # off — every skill would still read as disabled.
        if not cfg.skills.enabled:
            cfg.skills.enabled = True
    else:
        # Add to disabled_skills if not present
        if norm_name not in [s.strip().lower().replace("_", "-") for s in disabled_list]:
            disabled_list.append(norm_name)

    cfg.skills.disabled_skills = disabled_list

    try:
        cfg.save()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {e}")

    return {
        "status": "success",
        "name": name,
        "enabled": request.enabled,
    }
