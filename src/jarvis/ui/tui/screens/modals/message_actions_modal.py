"""
Message Actions Modal — Actions popup for user messages (Revert, Copy, Fork).

Displays a compact modal when a user message is clicked, allowing the user
to revert (undo) messages, copy the message text, or fork the session.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option


class MessageActionsModal(ModalScreen[dict[str, Any] | None]):
    """Modal displaying message actions: Revert, Copy."""

    DEFAULT_CSS = """
    MessageActionsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #message-actions-card {
        width: 62;
        height: 9;
        max-height: 80%;
        background: $surface;
        padding: 1 2;
    }

    #message-actions-card .title-bar {
        height: 1;
        layout: horizontal;
    }

    #message-actions-card .title-text {
        width: 1fr;
        text-style: bold;
        color: #ffffff;
    }

    #message-actions-card .esc-hint {
        width: auto;
        color: #737373;
    }

    #message-actions-card .list-wrapper {
        height: 1fr;
        align: center middle;
    }

    #message-actions-card .actions-list {
        height: auto;
        min-height: 0;
        background: transparent;
        border: none;
        scrollbar-size: 0 0;
        width: 100%;
    }

    #message-actions-card .actions-list > .option-list--option-highlighted {
        background: $primary 20%;
        color: $foreground;
        text-style: bold;
    }

    #message-actions-card .actions-list > .option-list--option-hover {
        background: $primary 15%;
    }
    """

    def __init__(
        self,
        message_text: str,
        message_index: int,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.message_text = message_text
        self.message_index = message_index

    def compose(self):
        with Vertical(id="message-actions-card"):
            with Horizontal(classes="title-bar"):
                yield Static("Message Actions", classes="title-text")
                yield Static("esc", classes="esc-hint")
            with Vertical(classes="list-wrapper"):
                yield OptionList(classes="actions-list")

    def on_mount(self) -> None:
        option_list = self.query_one(".actions-list", OptionList)
        option_list.clear_options()

        # Option 1: Revert
        revert_text = Text()
        revert_text.append("  Revert ", style="bold #60a5fa")
        revert_text.append("undo messages and file changes", style="#737373")
        option_list.add_option(Option(revert_text, id="revert"))

        # Option 2: Copy
        copy_text = Text()
        copy_text.append("  Copy ", style="bold #60a5fa")
        copy_text.append("message text to clipboard", style="#737373")
        option_list.add_option(Option(copy_text, id="copy"))

        option_list.highlighted = 0
        option_list.focus()

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if opt_id in ("revert", "copy"):
            self.dismiss({
                "action": opt_id,
                "message_text": self.message_text,
                "message_index": self.message_index,
            })
        else:
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
