"""
Input Simulation Tool — Simulate low-level mouse and keyboard actions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class InputSimulationTool(BaseTool):
    """Simulate mouse clicks, movements, text typing, and keyboard shortcuts."""

    schema = ToolSchema(
        name="input_simulation",
        description="Simulate mouse clicks, text typing, or keyboard shortcuts (e.g. 'ctrl+c', 'win+r', 'enter').",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'click', 'double_click', 'right_click', 'type', 'hotkey', 'press_key', 'scroll'.",
                enum=["click", "double_click", "right_click", "type", "hotkey", "press_key", "scroll"],
                required=True,
            ),
            ToolParameter(
                name="x",
                type="integer",
                description="X screen coordinate for mouse actions.",
                required=False,
            ),
            ToolParameter(
                name="y",
                type="integer",
                description="Y screen coordinate for mouse actions.",
                required=False,
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Text to type (for 'type' action) or single key name (for 'press_key' action).",
                required=False,
            ),
            ToolParameter(
                name="keys",
                type="array",
                description="List of keys for hotkey combination (e.g. ['ctrl', 'c'], ['win', 'r'], ['alt', 'f4']).",
                required=False,
            ),
            ToolParameter(
                name="amount",
                type="integer",
                description="Scroll amount (clicks) for 'scroll' action.",
                required=False,
                default=3,
            ),
            ToolParameter(
                name="direction",
                type="string",
                description="Scroll direction: 'up' or 'down'.",
                enum=["up", "down"],
                required=False,
                default="down",
            ),
        ],
        keywords=["click", "type", "hotkey", "mouse", "keyboard", "press key", "shortcut"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()

    async def execute(self, **kwargs: Any) -> str:
        """Execute input simulation."""
        action = kwargs.get("action", "").lower().strip()
        x = kwargs.get("x")
        y = kwargs.get("y")
        text = kwargs.get("text", "")
        keys = kwargs.get("keys")
        amount = int(kwargs.get("amount", 3))
        direction = kwargs.get("direction", "down")

        if action == "click":
            cx, cy = await asyncio.to_thread(self.controller.click, x=x, y=y)
            return f"Clicked mouse at ({cx}, {cy})."

        elif action == "double_click":
            cx, cy = await asyncio.to_thread(self.controller.double_click, x=x, y=y)
            return f"Double-clicked mouse at ({cx}, {cy})."

        elif action == "right_click":
            cx, cy = await asyncio.to_thread(self.controller.right_click, x=x, y=y)
            return f"Right-clicked mouse at ({cx}, {cy})."

        elif action == "type":
            if not text:
                return "Error: 'text' parameter is required for 'type' action."
            if x is not None and y is not None:
                await asyncio.to_thread(self.controller.click, x=x, y=y)
                await asyncio.sleep(0.1)
            await asyncio.to_thread(self.controller.type_text, text)
            return f"Typed text ({len(text)} characters)."

        elif action == "hotkey":
            if not keys:
                return "Error: 'keys' array parameter is required for 'hotkey' action (e.g. ['ctrl', 's'])."
            await asyncio.to_thread(self.controller.press_hotkey, *keys)
            return f"Pressed keyboard hotkey: {'+'.join(keys)}"

        elif action == "press_key":
            key_name = text or (keys[0] if keys else "enter")
            await asyncio.to_thread(self.controller.press_key, key_name)
            return f"Pressed key: {key_name}"

        elif action == "scroll":
            await asyncio.to_thread(self.controller.scroll, amount=amount, direction=direction, x=x, y=y)
            return f"Scrolled mouse {direction} by {amount} units."

        else:
            return f"Unknown action '{action}'. Valid actions: click, double_click, right_click, type, hotkey, press_key, scroll."
