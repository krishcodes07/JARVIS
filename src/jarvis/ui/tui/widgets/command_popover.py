"""
Command Popover Widget — Autocomplete command list overlay when user types '/'.
Matches image 3 design.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.commands import SlashCommand, filter_commands


class CommandPopoverWidget(Widget):
    """Floating list widget showing matching slash commands."""

    DEFAULT_CSS = """
    CommandPopoverWidget {
        layer: overlay;
        dock: bottom;
        offset: -3 -7;
        width: 1fr;
        max-height: 10;
        height: auto;
        background: #1e1e1e;
        border: none;
        border-left: tall #3b82f6;
        margin: 0 1 0 1;
        padding: 0 1;
        display: none;
    }

    #popover-option-list {
        background: transparent;
        border: none;
        max-height: 8;
        padding: 0;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.option_list = OptionList(id="popover-option-list")
        self.current_commands: list[SlashCommand] = []

    def compose(self):
        yield self.option_list

    def update_query(self, query: str) -> bool:
        """Update popover content based on user input query starting with '/'.

        Returns:
            True if matching commands were found and popover should be visible.
        """
        if not self.is_mounted:
            return False

        matches = filter_commands(query)
        self.current_commands = matches
        self.option_list.clear_options()

        if not matches:
            self.styles.display = "none"
            return False

        for cmd in matches:
            t = Text()
            t.append(f"{cmd.name:<16}", style="bold #f97316")
            t.append(f" {cmd.description}", style="dim #cbd5e1")
            self.option_list.add_option(Option(t, id=cmd.name))

        if len(matches) > 0:
            self.option_list.highlighted = 0

        self.styles.display = "block"
        return True

    def hide(self) -> None:
        if self.is_mounted:
            self.styles.display = "none"

    def highlight_next(self) -> None:
        if not self.current_commands or not self.is_mounted:
            return
        curr = self.option_list.highlighted
        if curr is None:
            self.option_list.highlighted = 0
        else:
            self.option_list.highlighted = (curr + 1) % len(self.current_commands)

    def highlight_prev(self) -> None:
        if not self.current_commands or not self.is_mounted:
            return
        curr = self.option_list.highlighted
        if curr is None:
            self.option_list.highlighted = len(self.current_commands) - 1
        else:
            self.option_list.highlighted = (curr - 1 + len(self.current_commands)) % len(self.current_commands)

    def get_selected_command(self) -> SlashCommand | None:
        if not self.is_mounted or self.styles.display != "block":
            return None
        if self.option_list.highlighted is not None and 0 <= self.option_list.highlighted < len(
            self.current_commands
        ):
            return self.current_commands[self.option_list.highlighted]
        return None
