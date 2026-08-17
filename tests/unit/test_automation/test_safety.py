"""
Unit tests for SafetyGuard and emergency abort mechanisms.
"""

from __future__ import annotations

import pytest

from jarvis.automation.safety import (
    AutomationAbortedError,
    SafetyGuard,
)
from jarvis.automation.schemas import ActionType, AutomationAction, WindowInfo
from jarvis.core.config import AutomationConfig


def test_safety_guard_abort_trigger() -> None:
    guard = SafetyGuard()
    assert not guard.is_aborted

    guard.trigger_abort()
    assert guard.is_aborted

    with pytest.raises(AutomationAbortedError):
        guard.assert_not_aborted()

    guard.reset_abort()
    assert not guard.is_aborted
    guard.assert_not_aborted()  # Should not raise


def test_safety_guard_protected_app_restriction() -> None:
    config = AutomationConfig(
        protected_apps=["1password", "bitwarden", "windows security"]
    )
    guard = SafetyGuard(config)

    action = AutomationAction(action_type=ActionType.CLICK, coordinates=(100, 100))

    # Safe window
    safe_win = WindowInfo(
        handle=1001,
        title="Notepad - Untitled",
        class_name="Notepad",
    )
    is_safe, reason = guard.check_action_safety(action, safe_win)
    assert is_safe
    assert reason == ""

    # Protected window
    protected_win = WindowInfo(
        handle=1002,
        title="Bitwarden Vault - Unlocked",
        class_name="Chrome_WidgetWin_1",
    )
    is_safe_prot, reason_prot = guard.check_action_safety(action, protected_win)
    assert not is_safe_prot
    assert "protected application rule 'bitwarden'" in reason_prot.lower()


def test_safety_guard_destructive_keyword_blocking() -> None:
    config = AutomationConfig(require_confirmation_for_sensitive=True)
    guard = SafetyGuard(config)

    destructive_action = AutomationAction(
        action_type=ActionType.TYPE,
        text="rmdir /s /q C:\\Windows",
    )
    is_safe, reason = guard.check_action_safety(destructive_action)
    assert not is_safe
    assert "destructive pattern 'rmdir /s'" in reason.lower()


def test_pynput_hotkey_formatting() -> None:
    guard = SafetyGuard()
    formatted = guard._format_pynput_hotkey("ctrl+alt+q")
    assert formatted == "<ctrl>+<alt>+q"

    f12 = guard._format_pynput_hotkey("ctrl+f12")
    assert f12 == "<ctrl>+<f12>"
