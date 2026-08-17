"""
Unit tests for automation schemas and models.
"""

from __future__ import annotations

import pytest

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


def test_action_type_enum() -> None:
    assert ActionType.CLICK.value == "click"
    assert ActionType.TYPE.value == "type"
    assert ActionType.PRESS_HOTKEY.value == "press_hotkey"
    assert ActionType.LAUNCH_APP.value == "launch_app"
    assert ActionType.DONE.value == "done"
    assert ActionType.FAIL.value == "fail"


def test_automation_action_creation() -> None:
    action = AutomationAction(
        action_type=ActionType.CLICK,
        element_id=5,
        coordinates=(100, 200),
        reason="Click the Submit button",
    )
    assert action.action_type == ActionType.CLICK
    assert action.element_id == 5
    assert action.coordinates == (100, 200)
    assert action.reason == "Click the Submit button"


def test_ui_element_info() -> None:
    el = UIElementInfo(
        id=1,
        name="Save",
        control_type="Button",
        automation_id="btn_save",
        bounding_box=(50, 50, 100, 30),
        center_point=(100, 65),
    )
    assert el.id == 1
    assert el.name == "Save"
    assert el.center_point == (100, 65)


def test_automation_goal_lifecycle() -> None:
    goal = AutomationGoal(
        goal_id="test-123",
        goal="Open Notepad and type test",
        max_steps=10,
    )
    assert goal.status == AutomationGoalStatus.PENDING

    step = AutomationStep(
        step_number=1,
        action=AutomationAction(action_type=ActionType.LAUNCH_APP, target="notepad"),
        action_result="Launched notepad",
        success=True,
        duration_seconds=0.4,
    )
    goal.steps.append(step)
    assert len(goal.steps) == 1
    assert goal.steps[0].action.target == "notepad"
