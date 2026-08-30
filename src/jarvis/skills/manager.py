"""
Skill Manager — Utilities for discovering and loading JARVIS skills.
"""

from __future__ import annotations

import contextlib
import logging
import re
import shutil
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


def list_available_skills(
    config: Any = None,
    include_disabled: bool = False,
) -> list[dict[str, Any]]:
    """List all available skills across user home workspace and built-in skill directories.

    Args:
        config: Optional JarvisConfig instance.
        include_disabled: Also return skills switched off in configuration, each
            flagged with ``enabled: False``. The settings UI needs this — filtering
            them out made a disabled skill vanish, so it could never be re-enabled.

    Returns:
        A list of dicts with 'name', 'description', 'path', 'enabled' and 'custom'.
    """
    if config and hasattr(config, "skills") and not config.skills.enabled:
        if not include_disabled:
            logger.debug("Skills subsystem is disabled in configuration.")
            return []

    skill_dirs = get_skills_directories(config)
    user_root = get_user_skills_directory()
    skills: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for s_dir in skill_dirs:
        if not s_dir.exists():
            continue

        for child in sorted(s_dir.iterdir()):
            if child.is_dir() and not child.name.startswith(("_", ".")):
                norm_name = child.name.lower().replace("_", "-")
                if norm_name in seen_names:
                    continue

                disabled = is_skill_disabled(child.name, config)
                if disabled and not include_disabled:
                    logger.debug(f"Skill '{child.name}' is disabled by configuration, skipping.")
                    continue

                readme_path = child / "README.md"
                if not readme_path.exists():
                    readme_path = child / "readme.md"

                is_custom = False
                with contextlib.suppress(ValueError, OSError):
                    child.resolve().relative_to(user_root.resolve())
                    is_custom = True

                seen_names.add(norm_name)
                skills.append({
                    "name": child.name,
                    "description": extract_skill_description(readme_path),
                    "path": str(child),
                    "enabled": not disabled,
                    "custom": is_custom,
                })

    return skills


def get_user_skills_directory(create: bool = False) -> Path:
    """Return the writable user skills directory (``~/.jarvis/workspace/skills``).

    Skills created from the settings UI go here rather than into the packaged
    ``src/jarvis/skills`` tree, which may be read-only in an installed build.
    """
    from jarvis.core.config import get_jarvis_home

    path = get_jarvis_home() / "workspace" / "skills"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def slugify_skill_name(name: str) -> str:
    """Normalise a display name into a safe skill directory name.

    Strips anything that is not alphanumeric or a dash so the result can never
    escape the skills directory via ``..`` or an absolute path.
    """
    cleaned = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower())
    return cleaned.strip("-")[:64]


def derive_skill_name(content: str) -> str:
    """Pull a skill name out of pasted README content.

    Prefers a YAML front-matter ``name:``, then the first markdown heading.
    """
    text = (content or "").strip()
    if not text:
        return ""

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            front = text[3:end]
            match = re.search(r"^\s*name\s*:\s*(.+)$", front, re.MULTILINE)
            if match:
                slug = slugify_skill_name(match.group(1).strip().strip("\"'"))
                if slug:
                    return slug

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            slug = slugify_skill_name(stripped.lstrip("#").strip())
            if slug:
                return slug

    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return slugify_skill_name(" ".join(stripped.split()[:6]))

    return ""


def find_skill_directory(skill_name: str, config: Any = None) -> Path | None:
    """Locate an existing skill's directory across all candidate roots."""
    normalized = slugify_skill_name(skill_name)
    if not normalized:
        return None

    for s_dir in get_skills_directories(config):
        if not s_dir.exists():
            continue
        candidate = s_dir / normalized
        if candidate.is_dir():
            return candidate
        for child in s_dir.iterdir():
            if child.is_dir() and slugify_skill_name(child.name) == normalized:
                return child
    return None


def create_skill(
    content: str,
    name: str | None = None,
    config: Any = None,
    overwrite: bool = False,
) -> dict[str, str]:
    """Create a skill from pasted README markdown.

    Args:
        content: The full README.md body.
        name: Optional explicit name; derived from the content when omitted.
        config: Optional JarvisConfig, used to detect existing skills.
        overwrite: Replace an existing skill of the same name instead of failing.

    Returns:
        A dict with ``name``, ``description`` and ``path``.

    Raises:
        SkillLoadError: Empty content, unusable name, name collision, or write failure.
    """
    body = (content or "").strip()
    if not body:
        raise SkillLoadError("Skill content is empty — paste the README.md body first.")

    slug = slugify_skill_name(name or "") or derive_skill_name(body)
    if not slug:
        raise SkillLoadError(
            "Could not determine a skill name. Add a '# Title' heading or supply a name."
        )

    if not overwrite:
        existing = find_skill_directory(slug, config)
        if existing is not None:
            raise SkillLoadError(f"A skill named '{slug}' already exists at {existing}.")

    target = get_user_skills_directory(create=True) / slug
    try:
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text(body.rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        raise SkillLoadError(f"Failed to write skill '{slug}': {e}") from e

    # A freshly added skill should be usable immediately.
    if config is not None and hasattr(config, "skills"):
        disabled = list(getattr(config.skills, "disabled_skills", []) or [])
        remaining = [d for d in disabled if slugify_skill_name(d) != slug]
        if len(remaining) != len(disabled):
            config.skills.disabled_skills = remaining
            with contextlib.suppress(Exception):
                config.save()

    logger.info(f"Created skill '{slug}' at {target}")
    return {
        "name": slug,
        "description": extract_skill_description(target / "README.md"),
        "path": str(target),
    }


def delete_skill(skill_name: str, config: Any = None) -> str:
    """Delete a user-created skill directory.

    Only skills under the writable user directory can be removed; packaged
    built-ins are left alone so an update cannot be undone by accident.

    Raises:
        SkillNotFoundError: No such skill.
        SkillLoadError: The skill is packaged (not user-created), or deletion failed.
    """
    folder = find_skill_directory(skill_name, config)
    if folder is None:
        raise SkillNotFoundError(f"Skill '{skill_name}' not found.")

    user_root = get_user_skills_directory()
    try:
        folder.resolve().relative_to(user_root.resolve())
    except (ValueError, OSError) as e:
        raise SkillLoadError(
            f"Skill '{folder.name}' is built in and cannot be deleted. Disable it instead."
        ) from e

    try:
        shutil.rmtree(folder)
    except OSError as e:
        raise SkillLoadError(f"Failed to delete skill '{folder.name}': {e}") from e

    logger.info(f"Deleted skill '{folder.name}' from {folder}")
    return folder.name


def extract_skill_description(readme_path: Path) -> str:
    """Read a one-line description out of a skill README."""
    if not readme_path.exists():
        return "No description provided."

    try:
        content = readme_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to read skill description from {readme_path}: {e}")
        return "No description provided."

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith(">"):
            return line.lstrip("> ").strip()
        if len(line) > 10:
            return line
    return "No description provided."


def format_skills_for_prompt(config: Any = None) -> str:
    """Format available skills (name and description) for injection into the system prompt.

    Args:
        config: Optional JarvisConfig instance.

    Returns:
        Formatted markdown string describing available skills and how to fetch them with get_skill.
    """
    if config and hasattr(config, "skills") and not config.skills.enabled:
        return ""

    skills = list_available_skills(config=config)
    if not skills:
        return ""

    lines = [
        "### Available Skills (Procedural Workflows)",
        "When handling tasks matching any of these domains, use `get_skill(skill_name=...)` to retrieve the full step-by-step guidance, rules, and procedures before proceeding:",
    ]
    for s in skills:
        lines.append(f"- `{s['name']}`: {s['description']}")

    return "\n".join(lines)


def get_skill_readme(
    skill_name: str,
    config: Any = None,
    include_disabled: bool = False,
) -> str:
    """Get the full README content of a specific skill.

    Args:
        skill_name: Name of the skill directory (e.g. 'deep-research').
        config: Optional JarvisConfig instance.
        include_disabled: Read the README even when the skill is switched off.
            The settings UI previews disabled skills; the agent-facing tool does not.

    Returns:
        The markdown content of the skill README.md.

    Raises:
        SkillNotFoundError: If the skill is disabled, directory or README does not exist.
        SkillLoadError: If reading the README file fails.
    """
    if not include_disabled:
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

    available = ", ".join(
        s["name"] for s in list_available_skills(config, include_disabled=include_disabled)
    ) or "none"
    raise SkillNotFoundError(f"Skill '{skill_name}' not found. Available skills: {available}")
