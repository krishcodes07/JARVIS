"""
Window Control Tool — Manage desktop window placement, focus, maximize, and snapping.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class WindowControlTool(BaseTool):
    """List, focus, minimize, maximize, snap, and close desktop windows."""

    schema = ToolSchema(
        name="window_control",
        description="List open windows, focus a specific window, maximize, minimize, or snap windows (left/right/up).",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="The window operation: 'list', 'focus', 'maximize', 'minimize', 'snap', 'close'.",
                enum=["list", "focus", "maximize", "minimize", "snap", "close"],
                required=True,
            ),
            ToolParameter(
                name="window_title",
                type="string",
                description="Target window title or substring match (e.g. 'Visual Studio Code', 'Notepad', 'Chrome').",
                required=False,
            ),
            ToolParameter(
                name="direction",
                type="string",
                description="Snap direction for 'snap' action: 'left', 'right', 'up', or 'down'.",
                enum=["left", "right", "up", "down"],
                required=False,
                default="left",
            ),
        ],
        keywords=["window", "minimize", "maximize", "snap", "focus", "switch window", "desktop layout"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()
        self.uia = UIAGrounder()

    async def execute(self, **kwargs: Any) -> str:
        """Execute window control action."""
        action = kwargs.get("action", "").lower().strip()
        title = kwargs.get("window_title", "")
        direction = kwargs.get("direction", "left")

        if action == "list":
            wins = await asyncio.to_thread(self.uia.list_open_windows)
            if not wins:
                return "No open desktop windows detected."
            lines = ["### Open Desktop Windows:"]
            for w in wins:
                status = " (Active)" if w.is_active else ""
                lines.append(f"- **{w.title}** [Handle: {w.handle}, Size: {w.width}x{w.height}]{status}")
            return "\n".join(lines)

        elif action == "focus":
            if not title:
                return "Error: 'window_title' is required to focus a window."
            ok = await asyncio.to_thread(self.controller.focus_window, title)
            if ok:
                return f"Focused window matching '{title}'."
            return f"Could not find or focus window matching '{title}'."

        elif action == "maximize":
            ok = await asyncio.to_thread(self.controller.maximize_window, title if title else None)
            if ok:
                target_str = f"'{title}'" if title else "active window"
                return f"Maximized {target_str}."
            return "Failed to maximize window."

        elif action == "minimize":
            ok = await asyncio.to_thread(self.controller.minimize_window, title if title else None)
            if ok:
                target_str = f"'{title}'" if title else "active window"
                return f"Minimized {target_str}."
            return "Failed to minimize window."

        elif action == "snap":
            ok = await asyncio.to_thread(self.controller.snap_window, direction=direction, title_or_handle=title if title else None)
            if ok:
                target_str = f"'{title}'" if title else "active window"
                return f"Snapped {target_str} to {direction}."
            return f"Failed to snap window to {direction}."

        elif action == "close":
            if not title:
                return "Error: 'window_title' is required to close a window."
            ok = await asyncio.to_thread(self.controller.close_window, title)
            if ok:
                return f"Closed window '{title}'."
            return f"Could not find or close window '{title}'."

        else:
            return f"Unknown action '{action}'. Valid actions: list, focus, maximize, minimize, snap, close."
