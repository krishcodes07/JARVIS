"""
Notification Toast Widget — Floating toast notification component for JARVIS TUI.
"""

from __future__ import annotations

from typing import Literal

from rich.text import Text
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Static


class NotificationToast(Widget):
    """Floating notification toast component."""

    DEFAULT_CSS = """
    NotificationToast {
        layer: overlay;
        dock: right;
        margin-top: 1;
        margin-right: 2;
        width: auto;
        min-width: 45;
        max-width: 90;
        height: auto;
        background: #1e293b;
        color: #f8fafc;
        border-left: solid #3b82f6;
        padding: 1 2;
        content-align: center middle;
        text-align: center;
        display: none;
    }

    #toast-content {
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
        width: 100%;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = Static(id="toast-content")
        self._timer: Timer | None = None

    def compose(self):
        yield self.label

    def show_toast(
        self,
        message: str,
        title: str = "Notification",
        style: Literal["info", "success", "warning", "error"] = "info",
        duration: float = 3.5,
    ) -> None:
        """Display toast notification with message and auto-dismiss timer."""
        if not self.is_mounted:
            return

        border_colors = {
            "info": "#3b82f6",
            "success": "#22c55e",
            "warning": "#f59e0b",
            "error": "#ef4444",
        }
        self.styles.border_left = ("solid", border_colors.get(style, "#3b82f6"))

        t = Text(justify="center")
        t.append(f"ⓘ {title}\n", style="bold #38bdf8")
        t.append(message, style="#f8fafc")
        self.label.update(t)

        self.styles.display = "block"

        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_timer(duration, self.hide_toast)

    def hide_toast(self) -> None:
        """Hide the notification toast."""
        if self.is_mounted:
            self.styles.display = "none"
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
