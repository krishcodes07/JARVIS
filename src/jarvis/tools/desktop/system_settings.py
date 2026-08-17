"""
System Settings Tool — Adjust system brightness, lock PC, inspect battery, and send notifications.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class SystemSettingsTool(BaseTool):
    """System settings management: lock PC, adjust brightness, check battery, send toast notifications."""

    schema = ToolSchema(
        name="system_settings",
        description="System controls: lock workstation, adjust screen brightness (0-100), check battery status, or send toast notifications.",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'lock', 'brightness', 'battery', 'notify'.",
                enum=["lock", "brightness", "battery", "notify"],
                required=True,
            ),
            ToolParameter(
                name="value",
                type="integer",
                description="Brightness percentage (0-100) for 'brightness' action.",
                required=False,
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Title for toast notification.",
                required=False,
            ),
            ToolParameter(
                name="message",
                type="string",
                description="Message text for toast notification.",
                required=False,
            ),
        ],
        keywords=["lock pc", "brightness", "battery", "toast notification", "power", "screen lock", "display"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()

    async def execute(self, **kwargs: Any) -> str:
        """Execute system settings action."""
        action = kwargs.get("action", "").lower().strip()
        value = kwargs.get("value")
        title = kwargs.get("title", "JARVIS")
        message = kwargs.get("message", "")

        if action == "lock":
            ok = await asyncio.to_thread(self.controller.lock_workstation)
            if ok:
                return "Workstation locked successfully."
            return "Failed to lock workstation."

        elif action == "notify":
            if not message:
                return "Error: 'message' is required for 'notify' action."
            await asyncio.to_thread(self.controller.send_toast_notification, title, message)
            return f"Toast notification sent: [{title}] {message}"

        elif action == "battery":
            try:
                import psutil
                battery = psutil.sensors_battery()
                if battery is None:
                    return "Battery status: Desktop PC (No battery detected / Running on AC power)."
                plugged = "Plugged In (Charging)" if battery.power_plugged else "Discharging"
                return f"Battery: {battery.percent}% | Status: {plugged} | Remaining: {battery.secsleft // 60 if battery.secsleft > 0 else 'Unknown'} mins"
            except Exception as e:
                return f"Error querying battery status: {e}"

        elif action == "brightness":
            if value is None:
                return "Error: 'value' (0-100) is required for brightness adjustment."
            target_brightness = max(0, min(100, int(value)))
            try:
                ps_cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target_brightness})"
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return f"Display brightness set to {target_brightness}%."
                return f"Could not set brightness (Display may not support WMI brightness control): {res.stderr.strip()}"
            except Exception as e:
                return f"Failed setting brightness: {e}"

        else:
            return f"Unknown action '{action}'. Valid actions: lock, brightness, battery, notify."
