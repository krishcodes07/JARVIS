"""
Safety Guard — Emergency Failsafes, Abort Hotkeys & Application Protection.

Guarantees safety during automated computer execution:
- Global Emergency Abort Hotkey (Ctrl+Alt+Q)
- PyAutoGUI screen corner failsafe
- Protected / sensitive application blacklist
- Destructive action guardrails
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.automation.schemas import AutomationAction, WindowInfo
    from jarvis.core.config import AutomationConfig

logger = logging.getLogger(__name__)

# Default list of destructive / high-risk command keywords that require strict confirmation
DESTRUCTIVE_KEYWORDS = [
    "format ",
    "rmdir /s",
    "del /f /s /q",
    "del /s /q",
    "reg delete",
    "shutdown /s",
    "shutdown /r",
    "diskpart",
    "drop table",
    "drop database",
]


class AutomationAbortedError(Exception):
    """Raised when desktop automation is stopped via emergency abort or failsafe."""
    pass


class SafetyViolationError(Exception):
    """Raised when an automation action attempts to interact with a protected application."""
    pass


class SafetyGuard:
    """Monitors and enforces safety during autonomous desktop operation."""

    def __init__(self, config: AutomationConfig | None = None) -> None:
        self.config = config
        self._abort_event = threading.Event()
        self._hotkey_listener: Any | None = None
        self._is_listening = False

        # Configure PyAutoGUI failsafe
        try:
            import pyautogui
            pyautogui.FAILSAFE = config.failsafe if config else True
            pyautogui.PAUSE = 0.05
        except Exception:
            pass

    def start(self) -> None:
        """Start the global emergency abort hotkey listener in background."""
        if self._is_listening:
            return

        hotkey_str = self.config.emergency_hotkey if self.config else "ctrl+alt+q"
        # Format for pynput, e.g. "<ctrl>+<alt>+q"
        pynput_key = self._format_pynput_hotkey(hotkey_str)

        try:
            from pynput import keyboard

            def on_emergency_abort() -> None:
                logger.critical(f"EMERGENCY ABORT TRIGGERED via hotkey ({hotkey_str})!")
                self.trigger_abort()

            self._hotkey_listener = keyboard.GlobalHotKeys({pynput_key: on_emergency_abort})
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
            self._is_listening = True
            logger.info(f"Emergency abort listener active on '{hotkey_str}'.")
        except Exception as e:
            logger.warning(f"Could not initialize global emergency abort hotkey listener: {e}")

    def stop(self) -> None:
        """Stop the global hotkey listener."""
        if self._hotkey_listener:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None
        self._is_listening = False

    def trigger_abort(self) -> None:
        """Trigger immediate emergency abort."""
        self._abort_event.set()

    def reset_abort(self) -> None:
        """Reset the abort signal for a new task."""
        self._abort_event.clear()

    @property
    def is_aborted(self) -> bool:
        """Check if an abort has been requested."""
        return self._abort_event.is_set()

    def assert_not_aborted(self) -> None:
        """Raise AutomationAbortedError if emergency abort has been signaled."""
        if self.is_aborted:
            raise AutomationAbortedError("Desktop automation was aborted by user emergency stop.")

    def check_action_safety(
        self,
        action: AutomationAction,
        active_window: WindowInfo | None = None,
    ) -> tuple[bool, str]:
        """Verify that the planned action is safe to execute in the current window context."""
        if self.is_aborted:
            return False, "Automation was aborted by user emergency stop."

        # 1. Protected application check
        protected_apps = self.config.protected_apps if self.config else []
        if active_window and protected_apps:
            title_lower = (active_window.title or "").lower()
            class_lower = (active_window.class_name or "").lower()
            proc_lower = (active_window.process_name or "").lower()

            for app in protected_apps:
                app_clean = app.strip().lower()
                if not app_clean:
                    continue
                if (
                    app_clean in title_lower
                    or app_clean in class_lower
                    or app_clean in proc_lower
                ):
                    return (
                        False,
                        f"Safety violation: Target window '{active_window.title}' matches "
                        f"protected application rule '{app}'. Automation is restricted here.",
                    )

        # 2. Destructive text / command check
        if action.text:
            text_lower = action.text.lower()
            for kw in DESTRUCTIVE_KEYWORDS:
                if kw in text_lower:
                    if self.config and self.config.require_confirmation_for_sensitive:
                        return (
                            False,
                            f"Safety gate: Action text contains destructive pattern '{kw}'. "
                            f"Execution blocked for safety.",
                        )

        return True, ""

    def _format_pynput_hotkey(self, hotkey_str: str) -> str:
        """Translate 'ctrl+alt+q' into '<ctrl>+<alt>+q' format required by pynput."""
        parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
        formatted: list[str] = []
        for p in parts:
            if p in ("ctrl", "control"):
                formatted.append("<ctrl>")
            elif p == "alt":
                formatted.append("<alt>")
            elif p in ("shift", "win", "cmd", "super") or (p.startswith("f") and p[1:].isdigit()):
                formatted.append(f"<{p}>")
            else:
                formatted.append(p)
        return "+".join(formatted)
