"""
Get Skill Tool — Returns the full README instructions for a specified JARVIS skill.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.core.exceptions import SkillError
from jarvis.skills.manager import get_skill_readme
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class GetSkillTool(BaseTool):
    """Retrieve full procedural instructions and README for a specific skill."""

    schema = ToolSchema(
        name="get_skill",
        description=(
            "Retrieve the full procedural README documentation and step-by-step instructions for a specific JARVIS skill."
        ),
        category="basic",
        aliases=["read_skill", "show_skill", "load_skill"],
        keywords=["get", "skill", "readme", "procedure", "instructions"],
        parameters=[
            ToolParameter(
                name="skill_name",
                type="string",
                description="Name of the skill to retrieve (e.g. 'deep-research', 'code-review', 'bug-hunting').",
                required=True,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Fetch and return skill README markdown content."""
        skill_name = kwargs.get("skill_name") or kwargs.get("name")
        if not skill_name:
            return "Error: Parameter 'skill_name' is required."

        try:
            cfg = getattr(self, "config", None)
            return get_skill_readme(skill_name, config=cfg)
        except SkillError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Unexpected error loading skill '{skill_name}': {e}", exc_info=True)
            return f"Error loading skill '{skill_name}': {e}"
