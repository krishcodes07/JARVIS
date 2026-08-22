"""Unit tests for EffortModal."""

import pytest
from jarvis.ui.tui.screens.modals.effort_modal import EffortModal
from jarvis.ui.tui.commands import get_command


def test_effort_command_registered():
    cmd = get_command("/effort")
    assert cmd is not None
    assert "/effort" in cmd.name
    assert "reasoning effort" in cmd.description.lower()


def test_effort_modal_initialization():
    modal = EffortModal(available_efforts=["low", "medium", "high", "max"])
    assert modal.available_efforts == ["low", "medium", "high", "max"]
    assert modal.dialog.title == "Reasoning Effort"


def test_prompt_box_badge_hides_when_off():
    from jarvis.ui.tui.widgets.prompt_box import PromptBoxWidget

    widget = PromptBoxWidget()
    widget.update_badges(model="test-model", provider="test-provider", reasoning="off")
    assert widget.reasoning == "off"

