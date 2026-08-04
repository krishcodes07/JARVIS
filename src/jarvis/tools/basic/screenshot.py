"""
Screenshot Tool — Capture screenshots of the screen.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class ScreenshotTool(BaseTool):
    """Capture a screenshot of the screen or a specific area."""

    schema = ToolSchema(
        name="screenshot",
        description="Take a screenshot of the entire screen or a specific region.",
        category="basic",
        parameters=[
            ToolParameter(name="region", type="string", description="Region to capture: 'full' for entire screen, or 'x,y,width,height'", required=False, default="full"),
            ToolParameter(name="save_path", type="string", description="Path to save the screenshot", required=False),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Take a screenshot."""
        # TODO: Implement using Pillow or mss
        return "[Screenshot tool — not yet implemented]"
