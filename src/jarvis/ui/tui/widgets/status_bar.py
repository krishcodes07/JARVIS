"""
Status Bar Widget — Bottom status footer with improved spacing.
Displays location, git branch, and quick navigation hints.
"""

from __future__ import annotations

import os
import subprocess

from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget


class TipBarWidget(Widget):
    """Helpful tip message line with better spacing."""

    DEFAULT_CSS = """
    TipBarWidget {
        height: 1;
        content-align: left middle;
        margin: 1 0 0 2;
        padding: 0;
        color: #8ba1c0;
    }
    """

    def render(self) -> RenderResult:
        txt = Text()
        txt.append("💡 ", style="dim #fbbf24")
        txt.append("Tip: ", style="bold #94a3b8")
        txt.append("Type ", style="dim #94a3b8")
        txt.append("@", style="bold white")
        txt.append(" followed by a filename to attach files", style="dim #94a3b8")
        return txt


class StatusBarWidget(Widget):
    """Bottom status bar"""

    DEFAULT_CSS = """
    StatusBarWidget {
        height: 1;
        background: #000000;
        color: #737373;
        border: none;
        margin: 0 1 1 1;
        padding: 0;
    }
    """

    def __init__(self, version: str = "v0.1.0", **kwargs) -> None:
        super().__init__(**kwargs)
        self.version = version
        self.is_generating: bool = False
        self._cached_branch: str = "main"

    def on_mount(self) -> None:
        self._cached_branch = self._get_git_branch()

    def set_generating(self, generating: bool) -> None:
        self.is_generating = generating
        if self.is_mounted:
            self.refresh()

    def render(self) -> RenderResult:
        left = Text()
        left.append("  ")  # Offset slightly to the right
        if self.is_generating:
            left.append("esc ", style="bold #ffffff")
            left.append("interrupt", style="dim #a3a3a3")
            left_plain_len = 15
        else:
            cwd = os.getcwd()
            branch = self._cached_branch
            location = f"{cwd}:{branch}" if branch else cwd
            left.append(location, style="dim #a3a3a3")
            left_plain_len = len(location) + 2

        right_raw = "tab commands   ctrl+s sessions"

        try:
            width = self.size.width if (self.size and self.size.width > 0) else (self.app.size.width - 2)
        except Exception:
            width = 120

        right_len = len(right_raw)
        gap = max(1, width - left_plain_len - right_len)

        txt = Text(no_wrap=True, overflow="ellipsis")
        txt.append_text(left)
        txt.append(" " * gap)

        right = Text(no_wrap=True)
        right.append("tab ", style="bold #ffffff")
        right.append("commands", style="dim #a3a3a3")
        right.append("   ")
        right.append("ctrl+s ", style="bold #ffffff")
        right.append("sessions", style="dim #a3a3a3")

        txt.append_text(right)
        return txt

    @staticmethod
    def _get_git_branch() -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "main"
