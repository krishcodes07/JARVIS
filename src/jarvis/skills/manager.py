"""
Skill Manager — Utilities for discovering and loading JARVIS skills.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jarvis.core.exceptions import SkillLoadError, SkillNotFoundError

logger = logging.getLogger(__name__)

# Base skills directory path
DEFAULT_SKILLS_DIR = Path(__file__).parent


def get_skills_directories(config: Any = None) -> list[Path]:
    """Get all candidate skill directories (user home workspace skills, configured skills_dir, package default)."""
    dirs: list[Path] = []

    # 1. Configured skills_dir if provided
    if config and hasattr(config, "skills") and config.skills.skills_dir:
        configured_path = Path(config.skills.skills_dir)
        if not configured_path.is_absolute():
            cand_cwd = Path.cwd() / configured_path
            if cand_cwd.exists() and cand_cwd.is_dir():
                configured_path = cand_cwd
            else:
                from jarvis.core.config import PROJECT_ROOT
                configured_path = PROJECT_ROOT / configured_path
        if configured_path.exists() and configured_path.is_dir():
            dirs.append(configured_path)

    # 2. User home workspace skills directory (~/.jarvis/workspace/skills)
    try:
        from jarvis.core.config import get_jarvis_home
        user_skills = get_jarvis_home() / "workspace" / "skills"
        if user_skills.exists() and user_skills.is_dir() and user_skills not in dirs:
            dirs.append(user_skills)
    except Exception as e:
        logger.debug(f"Could not resolve user home skills dir: {e}")

    # 3. Built-in package default skills directory
    if DEFAULT_SKILLS_DIR.exists() and DEFAULT_SKILLS_DIR.is_dir() and DEFAULT_SKILLS_DIR not in dirs:
        dirs.append(DEFAULT_SKILLS_DIR)

    # 4. Fallback to root jarvis/skills if running from workspace root
    root_skills = Path.cwd() / "jarvis" / "skills"
    if root_skills.exists() and root_skills.is_dir() and root_skills not in dirs:
        dirs.append(root_skills)

    return dirs


def get_skills_directory(config: Any = None) -> Path:
    """Get primary skills directory for backward compatibility."""
    dirs = get_skills_directories(config)
    return dirs[0] if dirs else DEFAULT_SKILLS_DIR


def is_skill_disabled(skill_name: str, config: Any = None) -> bool:
    """Check if a specific skill is disabled in configuration."""
    if not config or not hasattr(config, "skills"):
        return False

    if not config.skills.enabled:
        return True

    disabled_list = getattr(config.skills, "disabled_skills", []) or []
    normalized_target = skill_name.strip().lower().replace("_", "-")
    normalized_disabled = [s.strip().lower().replace("_", "-") for s in disabled_list]

    return normalized_target in normalized_disabled


def list_available_skills(config: Any = None) -> list[dict[str, str]]:
    """List all available skills across user home workspace and built-in skill directories.

    Args:
        config: Optional JarvisConfig instance.

    Returns:
        A list of dictionaries containing 'name', 'description', and 'path'.
    """
    if config and hasattr(config, "skills") and not config.skills.enabled:
        logger.debug("Skills subsystem is disabled in configuration.")
        return []

    skill_dirs = get_skills_directories(config)
    skills: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for s_dir in skill_dirs:
        if not s_dir.exists():
            continue

        for child in sorted(s_dir.iterdir()):
            if child.is_dir() and not child.name.startswith(("_", ".")):
                norm_name = child.name.lower().replace("_", "-")
                if norm_name in seen_names:
                    continue

                if is_skill_disabled(child.name, config):
                    logger.debug(f"Skill '{child.name}' is disabled by configuration, skipping.")
                    continue

                readme_path = child / "README.md"
                if not readme_path.exists():
                    readme_path = child / "readme.md"

                description = "No description provided."
                if readme_path.exists():
                    try:
                        content = readme_path.read_text(encoding="utf-8").strip()
                        lines = [line.strip() for line in content.splitlines() if line.strip()]

                        # Look for description under title or first paragraph
                        for line in lines:
                            if line.startswith("#"):
                                continue
                            if line.startswith(">"):
                                description = line.lstrip("> ").strip()
                                break
                            if len(line) > 10:
                                description = line
                                break
                    except Exception as e:
                        logger.warning(f"Failed to read skill description from {readme_path}: {e}")

                seen_names.add(norm_name)
                skills.append({
                    "name": child.name,
                    "description": description,
                    "path": str(child),
                })

    return skills


def get_skill_readme(skill_name: str, config: Any = None) -> str:
    """Get the full README content of a specific skill.

    Args:
        skill_name: Name of the skill directory (e.g. 'deep-research').
        config: Optional JarvisConfig instance.

    Returns:
        The markdown content of the skill README.md.

    Raises:
        SkillNotFoundError: If the skill is disabled, directory or README does not exist.
        SkillLoadError: If reading the README file fails.
    """
    if config and hasattr(config, "skills") and not config.skills.enabled:
        raise SkillNotFoundError("Skills subsystem is currently disabled in configuration.")

    if is_skill_disabled(skill_name, config):
        raise SkillNotFoundError(f"Skill '{skill_name}' is currently disabled in configuration.")

    normalized_name = skill_name.strip().lower().replace("_", "-")
    skill_dirs = get_skills_directories(config)

    for s_dir in skill_dirs:
        if not s_dir.exists():
            continue

        skill_folder = s_dir / normalized_name
        if not skill_folder.exists() or not skill_folder.is_dir():
            matching = [d for d in s_dir.iterdir() if d.is_dir() and d.name.lower().replace("_", "-") == normalized_name]
            if matching:
                skill_folder = matching[0]

        if skill_folder.exists() and skill_folder.is_dir():
            readme_path = skill_folder / "README.md"
            if not readme_path.exists():
                readme_path = skill_folder / "readme.md"

            if readme_path.exists():
                try:
                    return readme_path.read_text(encoding="utf-8")
                except Exception as e:
                    raise SkillLoadError(f"Failed to load README for skill '{skill_folder.name}': {e}") from e

    available = ", ".join(s["name"] for s in list_available_skills(config)) or "none"
    raise SkillNotFoundError(f"Skill '{skill_name}' not found. Available skills: {available}")
