"""
Helper Utilities for JARVIS TUI.
Common keyboard navigation delegation, string formatting, date formatting, clipboard, and git branch helpers.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.events import Key
    from textual.widgets import Input, OptionList


def handle_search_key_navigation(event: Key, search_input: Input | None, option_list: OptionList) -> bool:
    """Delegate Up/Down arrow navigation and Enter selection from search input to OptionList.

    Args:
        event: Textual Key event.
        search_input: Search Input widget.
        option_list: Modal OptionList widget.

    Returns:
        True if key event was handled and stopped, False otherwise.
    """
    if search_input and (search_input.has_focus or option_list.has_focus):
        if event.key == "up":
            event.stop()
            option_list.action_cursor_up()
            if hasattr(option_list, "scroll_to_highlight"):
                option_list.scroll_to_highlight()
            return True
        if event.key == "down":
            event.stop()
            option_list.action_cursor_down()
            if hasattr(option_list, "scroll_to_highlight"):
                option_list.scroll_to_highlight()
            return True
        if event.key == "enter":
            event.stop()
            option_list.action_select()
            return True
    return False


def truncate_text(text: str, max_length: int = 48, ellipsis: str = "...") -> str:
    """Truncate text to max_length with ellipsis if longer."""
    if not text:
        return ""
    clean = text.strip()
    if len(clean) > max_length:
        return clean[: max_length - len(ellipsis)] + ellipsis
    return clean


def format_tool_name(name: str) -> str:
    """Format tool_name into title case display name (e.g. 'search_web' -> 'Search Web')."""
    if not name:
        return ""
    return name.replace("_", " ").title()


def format_date_group(mtime: datetime, today_str: str) -> str:
    """Format modification datetime into date section group header ('Today' or 'Mon Aug 03 2026')."""
    date_str = mtime.strftime("%Y-%m-%d")
    return "Today" if date_str == today_str else mtime.strftime("%a %b %d %Y")


def get_git_branch() -> str:
    """Retrieve current git branch name asynchronously/sync fallback, default 'main'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "main"


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Copy text to system clipboard using pyperclip if available.

    Returns:
        Tuple of (success_boolean, message).
    """
    if not text:
        return False, "No content available to copy"
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True, "Copied last AI response to clipboard"
    except Exception as e:
        return False, f"Could not copy to clipboard: {e}"
