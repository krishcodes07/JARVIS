"""
List Skills Tool — Lists all available JARVIS procedural skills and brief descriptions.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.skills.manager import list_available_skills
from jarvis.tools.base import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class ListSkillsTool(BaseTool):
    """List all available JARVIS skills with brief descriptions."""

    schema = ToolSchema(
        name="list_skills",
        description=(
            "List all available procedural skills in JARVIS along with brief descriptions. "
            "Use get_skill(skill_name=...) to retrieve the full step-by-step instructions and README for a skill."
        ),
        category="basic",
        aliases=["show_skills", "available_skills"],
        keywords=["list", "skills", "workflows", "procedures"],
        parameters=[],
    )

    async def execute(self, **kwargs: Any) -> str:
        """List all available skills."""
        cfg = getattr(self, "config", None)
        skills = list_available_skills(config=cfg)

        if not skills:
            return "No skills found."

        lines = ["Available JARVIS Skills:"]
        for skill in skills:
            lines.append(f"- **{skill['name']}**: {skill['description']}")

        return "\n".join(lines)
