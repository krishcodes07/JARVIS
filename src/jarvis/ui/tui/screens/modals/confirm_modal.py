"""
Confirm Modal Screen — Reusable dialog for confirming actions (e.g. deleting session).
"""

from __future__ import annotations

from rich.text import Text
from textual import on
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from jarvis.ui.tui.widgets.modal_dialog import ModalDialog


class ConfirmModal(ModalScreen[bool]):
    """Confirmation modal dialog returning True on confirm and False on cancel."""

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }
    """

    def __init__(
        self,
        message: str = "Are you sure you want to proceed?",
        title: str = "Confirm Action",
        confirm_label: str = "Yes, delete",
        cancel_label: str = "No, cancel",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.message_text = message
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.dialog = ModalDialog(
            title=title,
            dialog_id="confirm-dialog",
            width=58,
            height=14,
            show_search=False,
            footer_text="Enter select   y yes   n / Esc cancel",
            border_style="solid #ef4444",
        )

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        self.option_list.clear_options()

        # Add message header option (disabled)
        msg_text = Text(f"  {self.message_text}\n", style="bold #ffffff")
        self.option_list.add_option(Option(msg_text, disabled=True))

        # Confirm choice
        confirm_text = Text(f"  ✓ {self.confirm_label}", style="bold #ef4444")
        self.option_list.add_option(Option(confirm_text, id="confirm"))

        # Cancel choice
        cancel_text = Text(f"  ✕ {self.cancel_label}", style="bold #a3a3a3")
        self.option_list.add_option(Option(cancel_text, id="cancel"))

        self.option_list.highlighted = 1
        self.option_list.focus()

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )
        if opt_id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def key_y(self) -> None:
        self.dismiss(True)

    def key_n(self) -> None:
        self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)
