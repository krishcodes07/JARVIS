"""
Clipboard Tool — Copy and paste from system clipboard.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class ClipboardTool(BaseTool):
    """Interact with the system clipboard."""

    schema = ToolSchema(
        name="clipboard",
        description="Copy text to or paste text from the system clipboard.",
        category="basic",
        parameters=[
            ToolParameter(name="action", type="string", description="Action to perform: 'copy' or 'paste'"),
            ToolParameter(name="text", type="string", description="Text to copy (only for 'copy' action)", required=False),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute clipboard operation."""
        # TODO: Implement using pyperclip or native APIs
        action = kwargs["action"]
        if action == "copy":
            text = kwargs.get("text", "")
            return f"Copied to clipboard: {text[:50]}..."
        elif action == "paste":
            return "[Clipboard paste — not yet implemented]"
        return f"Unknown action: {action}"
