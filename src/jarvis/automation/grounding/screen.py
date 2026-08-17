"""
Screen Geometry & DPI Scaling Helper.

Ensures proper Windows DPI awareness and translates coordinates reliably.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ScreenBounds(NamedTuple):
    left: int
    top: int
    width: int
    height: int
    right: int
    bottom: int


def enable_dpi_awareness() -> None:
    """Set process DPI awareness on Windows to prevent coordinate scaling mismatches."""
    if sys.platform != "win32":
        return
    try:
        # Per-monitor DPI aware (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.debug("Set per-monitor DPI awareness.")
    except Exception:
        try:
            # System DPI aware fallback
            ctypes.windll.user32.SetProcessDPIAware()
            logger.debug("Set system DPI awareness fallback.")
        except Exception as e:
            logger.warning(f"Could not set DPI awareness: {e}")


class ScreenManager:
    """Manages multi-monitor dimensions and coordinate conversions."""

    def __init__(self) -> None:
        enable_dpi_awareness()

    def get_primary_resolution(self) -> tuple[int, int]:
        """Return (width, height) of primary screen in physical pixels."""
        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                if w > 0 and h > 0:
                    return w, h
            except Exception:
                pass

        try:
            import pyautogui
            sz = pyautogui.size()
            return sz.width, sz.height
        except Exception:
            return 1920, 1080

    def get_screen_bounds(self) -> ScreenBounds:
        """Get the full bounding rectangle of the primary display."""
        w, h = self.get_primary_resolution()
        return ScreenBounds(left=0, top=0, width=w, height=h, right=w, bottom=h)

    def clamp_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """Clamp coordinates within screen bounds to avoid out-of-range errors."""
        w, h = self.get_primary_resolution()
        clamped_x = max(0, min(x, w - 1))
        clamped_y = max(0, min(y, h - 1))
        return clamped_x, clamped_y

    def normalized_to_pixels(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        """Convert normalized (0.0 - 1.0) coordinates to physical pixel coordinates."""
        w, h = self.get_primary_resolution()
        return round(norm_x * w), round(norm_y * h)

    def pixels_to_normalized(self, x: int, y: int) -> tuple[float, float]:
        """Convert physical pixel coordinates to normalized (0.0 - 1.0) coordinates."""
        w, h = self.get_primary_resolution()
        return round(x / max(w, 1), 4), round(y / max(h, 1), 4)
