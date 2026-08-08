"""
Status Bar Widget — Bottom status footer with improved spacing.
Displays location, git branch, and quick navigation hints.
"""

from __future__ import annotations

import os

from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget

from jarvis.ui.tui.utils import get_git_branch


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


def format_context_usage(tokens: int, limit: int) -> str:
    """Format token context usage and percentage, e.g., '5.5k (3%)' or '850 (1%)'."""
    if limit <= 0:
        limit = 128000

    if tokens < 1000:
        tok_str = str(tokens)
    elif tokens < 100000:
        tok_str = f"{tokens / 1000:.1f}k"
    else:
        tok_str = f"{tokens // 1000}k"

    pct = round((tokens / limit) * 100)
    pct = max(0, min(100, pct))
    return f"{tok_str} ({pct}%)"


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
        self.context_tokens: int | None = None
        self.context_limit: int | None = None

    def on_mount(self) -> None:
        self._cached_branch = get_git_branch()

    def set_generating(self, generating: bool) -> None:
        self.is_generating = generating
        if self.is_mounted:
            self.refresh()

    def set_context_usage(self, tokens: int, limit: int) -> None:
        """Update context window usage."""
        self.context_tokens = tokens
        self.context_limit = limit
        if self.is_mounted:
            self.refresh()

    def clear_context_usage(self) -> None:
        """Clear context window usage display (resets back to tab commands)."""
        self.context_tokens = None
        self.context_limit = None
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

        if self.context_tokens is not None and self.context_limit is not None:
            context_str = format_context_usage(self.context_tokens, self.context_limit)
            right_raw = f"{context_str}   ctrl+s sessions"
        else:
            context_str = None
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
        if context_str:
            right.append(context_str, style="dim #a3a3a3")
            right.append("   ")
        else:
            right.append("tab ", style="bold #ffffff")
            right.append("commands", style="dim #a3a3a3")
            right.append("   ")

        right.append("ctrl+s ", style="bold #ffffff")
        right.append("sessions", style="dim #a3a3a3")

        txt.append_text(right)
        return txt

