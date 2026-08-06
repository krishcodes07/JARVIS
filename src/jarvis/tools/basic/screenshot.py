"""
Screenshot Tool — Capture screenshots of the screen.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def _take_screenshot(save_path: Path, region_str: str = "full") -> tuple[int, int]:
    """Capture screen and save to save_path. Returns (width, height)."""
    region_str = (region_str or "full").strip().lower()
    bbox: tuple[int, int, int, int] | None = None
    if region_str != "full":
        parts = [p.strip() for p in region_str.split(",") if p.strip()]
        if len(parts) != 4:
            raise ValueError("Region must be 'full' or formatted as 'x,y,width,height'")
        try:
            bbox = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        except ValueError as err:
            raise ValueError(f"Invalid numeric values in region '{region_str}': {err}") from err

    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Try mss first (fast, multi-monitor support)
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            if bbox:
                monitor: dict[str, int] = {
                    "left": bbox[0],
                    "top": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3],
                }
            else:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(save_path))
            return sct_img.width, sct_img.height
    except Exception as mss_err:
        logger.debug(f"mss screenshot failed, falling back to ImageGrab: {mss_err}")

    # Fallback to PIL ImageGrab
    from PIL import ImageGrab

    if bbox:
        img = ImageGrab.grab(bbox=(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]))
    else:
        img = ImageGrab.grab(all_screens=True)
    img.save(str(save_path))
    return img.width, img.height


class ScreenshotTool(BaseTool):
    """Capture a screenshot of the screen or a specific area."""

    schema = ToolSchema(
        name="screenshot",
        description="Take a screenshot of the entire screen or a specific region.",
        category="basic",
        parameters=[
            ToolParameter(
                name="region",
                type="string",
                description="Region to capture: 'full' for entire screen, or 'x,y,width,height'",
                required=False,
                default="full",
            ),
            ToolParameter(
                name="save_path",
                type="string",
                description="Path to save the screenshot",
                required=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Take a screenshot."""
        region = kwargs.get("region", "full")
        save_path_str = kwargs.get("save_path")

        if save_path_str:
            target_path = Path(save_path_str)
            if not target_path.is_absolute():
                target_path = PROJECT_ROOT / target_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = PROJECT_ROOT / "data" / "cache" / "screenshots" / f"screenshot_{timestamp}.png"

        try:
            width, height = await asyncio.to_thread(_take_screenshot, target_path, region)
            return (
                f"Screenshot saved successfully to '{target_path}' "
                f"(Resolution: {width}x{height}px)."
            )
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}", exc_info=True)
            return f"Error taking screenshot: {e}"
