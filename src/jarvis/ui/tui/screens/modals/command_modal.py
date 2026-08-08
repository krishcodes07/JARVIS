"""
Command Palette Modal Screen — Floating dialog for slash commands selection (Ctrl+P / /).
Matches Image 3 design.
"""

from __future__ import annotations

from rich.text import Text
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.commands import SlashCommand, filter_commands
from jarvis.ui.tui.utils import handle_search_key_navigation
from jarvis.ui.tui.widgets.modal_dialog import ModalDialog


class CommandModal(ModalScreen[SlashCommand | None]):
    """Command palette dialog displaying slash commands."""

    DEFAULT_CSS = """
    CommandModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(self, initial_query: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.initial_query = initial_query
        self.dialog = ModalDialog(
            title="Commands",
            dialog_id="cmd-dialog",
            width=76,
            height="80%",
            show_search=True,
            search_placeholder="Type command...",
            border_style="solid #3b82f6",
        )
        self.current_commands: list[SlashCommand] = []

    @property
    def search_input(self) -> Input | None:
        return self.dialog.search_input

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        if self.search_input:
            if self.initial_query:
                self.search_input.value = self.initial_query
            self.search_input.focus()
        self.populate_list(self.initial_query)

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(filter_text=event.value)

    def on_key(self, event) -> None:
        """Delegate arrow keys and Enter from search input to the option list."""
        handle_search_key_navigation(event, self.search_input, self.option_list)

    def populate_list(self, filter_text: str = "") -> None:
        if not self.is_mounted:
            return
        self.option_list.clear_options()
        matches = filter_commands(filter_text)
        self.current_commands = matches

        for cmd in matches:
            t = Text()
            t.append(f"{cmd.name:<18}", style="bold #f97316")
            t.append(f" {cmd.description:<45}", style="dim #e2e8f0")
            if cmd.usage:
                t.append(f" {cmd.usage}", style="dim #64748b")

            self.option_list.add_option(Option(t, id=cmd.name))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if selected_id:
            found = next((c for c in self.current_commands if c.name == selected_id), None)
            if found:
                self.dismiss(found)
                return
        idx = getattr(event, "option_index", None)
        if idx is not None and 0 <= idx < len(self.current_commands):
            self.dismiss(self.current_commands[idx])
            return
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
