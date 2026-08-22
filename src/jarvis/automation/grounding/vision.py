"""
Visual Grounder — Set-of-Marks (SoM) & Screenshot Perception Engine.

Provides screenshot capture, Set-of-Marks visual element annotations,
and visual delta verification for confirming UI state transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jarvis.automation.grounding.screen import ScreenManager
from jarvis.core.paths import get_cache_dir

if TYPE_CHECKING:
    from jarvis.automation.schemas import UIElementInfo

logger = logging.getLogger(__name__)


class VisualGrounder:
    """Handles visual screenshot capturing, Set-of-Marks (SoM) annotation, and visual verification."""

    def __init__(self) -> None:
        self.screen_manager = ScreenManager()

    def capture_screenshot(self, save_path: Path | None = None) -> Path:
        """Capture the current primary screen to a PNG file."""
        if save_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            save_path = get_cache_dir() / "automation_logs" / f"screen_{ts}.png"

        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Fast capture using mss
        try:
            import mss
            import mss.tools

            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(save_path))
                return save_path
        except Exception as err:
            logger.debug(f"mss capture fallback to PIL: {err}")

        # Fallback to PIL ImageGrab
        from PIL import ImageGrab

        img = ImageGrab.grab(all_screens=False)
        img.save(str(save_path))
        return save_path

    def annotate_set_of_marks(
        self,
        screenshot_path: Path,
        elements: list[UIElementInfo],
        output_path: Path | None = None,
    ) -> Path:
        """Overlay distinct, labeled Set-of-Marks bounding boxes and ID badges on the screenshot."""
        from PIL import Image, ImageDraw, ImageFont

        if output_path is None:
            output_path = screenshot_path.with_stem(f"{screenshot_path.stem}_som")

        with Image.open(screenshot_path) as raw_image:
            image = raw_image.convert("RGBA").copy()

        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Color palette for badges
        colors = [
            (255, 59, 48, 200),   # Red
            (0, 122, 255, 200),   # Blue
            (52, 199, 89, 200),   # Green
            (255, 149, 0, 200),   # Orange
            (175, 82, 222, 200),  # Purple
            (0, 199, 190, 200),   # Teal
        ]

        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        for idx, el in enumerate(elements):
            x, y, w, h = el.bounding_box
            if w <= 0 or h <= 0:
                continue

            color = colors[idx % len(colors)]
            outline_color = (color[0], color[1], color[2], 255)

            # Draw bounding rectangle outline
            draw.rectangle([x, y, x + w, y + h], outline=outline_color, width=2)

            # Draw badge with element ID
            label = str(el.id)
            badge_w = max(20, len(label) * 10 + 6)
            badge_h = 18

            # Position badge at top-left corner of the element
            bx = max(0, min(x, image.width - badge_w))
            by = max(0, y - badge_h) if y >= badge_h else y

            draw.rectangle([bx, by, bx + badge_w, by + badge_h], fill=color, outline=(255, 255, 255, 255))
            draw.text((bx + 4, by + 1), label, fill=(255, 255, 255, 255), font=font)

        # Composite and save
        combined = Image.alpha_composite(image, overlay).convert("RGB")
        combined.save(str(output_path), "PNG")
        return output_path

    def compute_visual_delta(self, before_path: Path, after_path: Path) -> float:
        """Compute the visual change percentage between two screenshots (0.0 - 1.0)."""
        from PIL import Image, ImageChops, ImageStat

        try:
            with Image.open(before_path) as b_img, Image.open(after_path) as a_img:
                img1 = b_img.convert("L")
                img2 = a_img.convert("L")

                # Resize if dimensions differ
                if img1.size != img2.size:
                    img2 = img2.resize(img1.size)

                diff = ImageChops.difference(img1, img2)
                stat = ImageStat.Stat(diff)
                mean_delta = stat.mean[0] / 255.0
                return round(mean_delta, 4)
        except Exception as e:
            logger.debug(f"Error computing visual delta: {e}")
            return 0.0
