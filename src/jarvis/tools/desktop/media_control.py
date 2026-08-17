"""
Media Control Tool — Adjust Windows system volume, mute, and media playback keys.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class MediaControlTool(BaseTool):
    """Control system audio volume, mute state, and media playback."""

    schema = ToolSchema(
        name="media_control",
        description="Control PC volume (0-100%), mute/unmute audio, or trigger play/pause, next track, and previous track.",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'set_volume', 'get_volume', 'mute', 'unmute', 'play_pause', 'next', 'prev', 'stop'.",
                enum=["set_volume", "get_volume", "mute", "unmute", "play_pause", "next", "prev", "stop"],
                required=True,
            ),
            ToolParameter(
                name="volume",
                type="integer",
                description="Volume percentage from 0 to 100 (for 'set_volume' action).",
                required=False,
            ),
        ],
        keywords=["volume", "sound", "mute", "unmute", "audio", "play", "pause", "music", "spotify", "media"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()

    async def execute(self, **kwargs: Any) -> str:
        """Execute media control action."""
        action = kwargs.get("action", "").lower().strip()
        volume = kwargs.get("volume")

        if action == "set_volume":
            if volume is None:
                return "Error: 'volume' (0-100) parameter is required for 'set_volume' action."
            res = await asyncio.to_thread(self.controller.set_master_volume, int(volume))
            if res >= 0:
                return f"System volume set to {res}%."
            return "Failed to adjust volume via Windows Core Audio API."

        elif action == "get_volume":
            curr_vol = await asyncio.to_thread(self.controller.get_master_volume)
            if curr_vol >= 0:
                return f"Current master volume is {curr_vol}%."
            return "Unable to determine current audio volume."

        elif action == "mute":
            await asyncio.to_thread(self.controller.mute_master_volume, True)
            return "Master audio muted."

        elif action == "unmute":
            await asyncio.to_thread(self.controller.mute_master_volume, False)
            return "Master audio unmuted."

        elif action in ("play_pause", "play", "pause"):
            await asyncio.to_thread(self.controller.send_media_key, "play_pause")
            return "Sent media Play/Pause command."

        elif action in ("next", "next_track"):
            await asyncio.to_thread(self.controller.send_media_key, "next")
            return "Skipped to next media track."

        elif action in ("prev", "prev_track", "previous"):
            await asyncio.to_thread(self.controller.send_media_key, "prev")
            return "Returned to previous media track."

        elif action == "stop":
            await asyncio.to_thread(self.controller.send_media_key, "stop")
            return "Stopped media playback."

        else:
            return f"Unknown action '{action}'. Valid actions: set_volume, get_volume, mute, unmute, play_pause, next, prev, stop."
