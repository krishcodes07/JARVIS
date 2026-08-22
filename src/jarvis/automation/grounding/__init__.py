"""
Grounding Package — Screen geometry, Windows UIA, and Visual Perception.
"""

from jarvis.automation.grounding.screen import ScreenManager, enable_dpi_awareness
from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.automation.grounding.vision import VisualGrounder

__all__ = [
    "ScreenManager",
    "UIAGrounder",
    "VisualGrounder",
    "enable_dpi_awareness",
]
