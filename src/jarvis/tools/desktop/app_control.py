"""
App Control Tool — Launch, switch, list, and close desktop applications.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class AppControlTool(BaseTool):
    """Launch, list, focus, or close desktop applications."""

    schema = ToolSchema(
        name="app_control",
        description="Launch applications, list running desktop apps, focus an application window, or close/terminate an app.",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="The action to perform: 'launch', 'list', 'focus', 'close', or 'terminate'.",
                enum=["launch", "list", "focus", "close", "terminate"],
                required=True,
            ),
            ToolParameter(
                name="app_name",
                type="string",
                description="Application name, executable name, or window title (e.g. 'notepad', 'calc', 'chrome', 'spotify', 'code').",
                required=False,
            ),
            ToolParameter(
                name="args",
                type="array",
                description="Optional command-line arguments to pass when launching the application.",
                required=False,
            ),
        ],
        keywords=["app", "launch", "open app", "close app", "kill process", "focus app", "running apps"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()
        self.uia = UIAGrounder()

    async def execute(self, **kwargs: Any) -> str:
        """Execute app control action."""
        action = kwargs.get("action", "").lower().strip()
        app_name = kwargs.get("app_name", "")
        args = kwargs.get("args")

        if action == "launch":
            if not app_name:
                return "Error: 'app_name' parameter is required for 'launch' action."
            res = await asyncio.to_thread(self.controller.launch_app, app_name, args)
            return res

        elif action == "list":
            windows = await asyncio.to_thread(self.uia.list_open_windows)
            if not windows:
                return "No running graphical application windows found."
            lines = ["### Running Desktop Applications:"]
            for w in windows:
                active_flag = " (Active)" if w.is_active else ""
                lines.append(f"- **{w.title}** (PID: {w.process_id}, Class: {w.class_name}){active_flag}")
            return "\n".join(lines)

        elif action == "focus":
            if not app_name:
                return "Error: 'app_name' or window title is required for 'focus' action."
            ok = await asyncio.to_thread(self.controller.focus_window, app_name)
            if ok:
                return f"Successfully focused window matching '{app_name}'."
            return f"Could not find or focus window matching '{app_name}'."

        elif action in ("close", "terminate"):
            if not app_name:
                return f"Error: 'app_name' is required for '{action}' action."
            force = (action == "terminate")
            ok = await asyncio.to_thread(self.controller.close_window, app_name, force=force)
            if ok:
                verb = "Terminated" if force else "Closed"
                return f"{verb} application window '{app_name}' successfully."
            return f"Failed to find or close application window '{app_name}'."

        else:
            return f"Unknown action '{action}'. Valid actions: launch, list, focus, close, terminate."
