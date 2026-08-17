"""
JARVIS Automation & PC Control Subsystem.

Provides complete autonomous computer control, UI Automation (UIA),
desktop actuation, and emergency safety guardrails.
"""

from jarvis.automation.agent import AutomationAgent
from jarvis.automation.controller import DesktopController
from jarvis.automation.engine import AutomationEngine
from jarvis.automation.grounding import ScreenManager, UIAGrounder, VisualGrounder
from jarvis.automation.safety import (
    AutomationAbortedError,
    SafetyGuard,
    SafetyViolationError,
)
from jarvis.automation.schemas import (
    ActionType,
    AutomationAction,
    AutomationGoal,
    AutomationGoalStatus,
    AutomationObservation,
    AutomationStep,
    UIElementInfo,
    WindowInfo,
)

__all__ = [
    "AutomationEngine",
    "AutomationAgent",
    "DesktopController",
    "UIAGrounder",
    "VisualGrounder",
    "ScreenManager",
    "SafetyGuard",
    "AutomationAbortedError",
    "SafetyViolationError",
    "ActionType",
    "AutomationAction",
    "AutomationGoal",
    "AutomationGoalStatus",
    "AutomationObservation",
    "AutomationStep",
    "UIElementInfo",
    "WindowInfo",
]
