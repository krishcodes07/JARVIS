"""
Message Actions Modal — Actions popup for user messages (Revert, Copy, Fork).

Displays a compact modal when a user message is clicked, allowing the user
to revert (undo) messages, copy the message text, or fork the session.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.widgets.modal_dialog import ModalDialog


class MessageActionsModal(ModalScreen[dict[str, Any] | None]):
    """Modal displaying message actions: Revert, Copy."""

    DEFAULT_CSS = """
    MessageActionsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
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
        self.dialog = ModalDialog(
            title="Message Actions",
            dialog_id="message-actions-dialog",
            width=62,
            height=9,
            show_search=False,
            border_style="none",
        )

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self.option_list.clear_options()

        # Option 1: Revert
        revert_text = Text()
        revert_text.append("  Revert ", style="bold #60a5fa")
        revert_text.append("undo messages and file changes", style="#737373")
        self.option_list.add_option(Option(revert_text, id="revert"))

        # Option 2: Copy
        copy_text = Text()
        copy_text.append("  Copy ", style="bold #60a5fa")
        copy_text.append("message text to clipboard", style="#737373")
        self.option_list.add_option(Option(copy_text, id="copy"))

        self.option_list.highlighted = 0
        self.option_list.focus()

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
