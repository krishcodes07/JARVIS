"""
Reusable Modal Dialog widget for JARVIS TUI.

Provides a consistent dark-themed dialog box with:
- Title bar (title + "esc" hint)
- Optional search input
- OptionList for selectable items
- Optional footer text
"""

from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.widgets import Input, OptionList, Static


class ModalDialog(Vertical):
    """A reusable modal dialog container with title bar, optional search, option list, and footer."""

    DEFAULT_CSS = """
    ModalDialog {
        background: #1a1a1a;
        border: none;
        padding: 1 2;
    }

    ModalDialog .modal-title-bar {
        height: 1;
        layout: horizontal;
    }

    ModalDialog .modal-title {
        width: 1fr;
        text-style: bold;
        color: #ffffff;
    }

    ModalDialog .modal-esc {
        width: auto;
        color: #737373;
    }

    ModalDialog .modal-search {
        background: #111111;
        border: solid #333333;
        margin: 1 0 0 0;
        color: #ffffff;
        height: 3;
        padding: 0 1;
    }

    ModalDialog .modal-search:focus {
        border: solid #3b82f6;
        background: #111111;
        color: #ffffff;
    }

    ModalDialog .modal-list {
        height: 1fr;
        background: transparent;
        border: none;
        scrollbar-size: 0 0;
        margin-bottom: 1;
    }

    /* Orange highlight for keyboard-navigated item */
    ModalDialog .modal-list > .option-list--option-highlighted {
        background: #f97316 20%;
        color: #ffffff;
    }

    ModalDialog .modal-list > .option-list--option-hover {
        background: #f97316 15%;
    }

    ModalDialog .modal-list > .option-list--option-highlighted-no-highlight {
        background: #f97316 20%;
    }

    ModalDialog .modal-footer {
        dock: bottom;
        height: 2;
        padding-top: 1;
        color: #737373;
        text-align: center;
        width: 100%;
    }
    """

    def __init__(
        self,
        title: str,
        *,
        dialog_id: str = "modal-dialog",
        width: int = 62,
        height: int = 22,
        show_search: bool = True,
        search_placeholder: str = "Search...",
        footer_text: str | None = None,
        border_style: str = "none",
        **kwargs,
    ) -> None:
        super().__init__(id=dialog_id, **kwargs)
        self._title_text = title
        self._dialog_width = width
        self._dialog_height = height
        self._show_search = show_search
        self._search_placeholder = search_placeholder
        self._footer_text = footer_text
        self._border_style = border_style

        self.search_input: Input | None = None
        self.option_list: OptionList = OptionList(classes="modal-list")

        if self._show_search:
            self.search_input = Input(
                placeholder=self._search_placeholder,
                classes="modal-search",
            )

        self.styles.width = self._dialog_width
        self.styles.height = self._dialog_height
        if self._border_style != "none":
            parts = self._border_style.split(" ", 1)
            if len(parts) == 2:
                self.styles.border = (parts[0], parts[1])  # type: ignore[assignment]
            elif len(parts) == 1:
                self.styles.border = (parts[0], "white")  # type: ignore[assignment]

    def compose(self):
        with Horizontal(classes="modal-title-bar"):
            yield Static(self._title_text, classes="modal-title")
            yield Static("esc", classes="modal-esc")
        if self.search_input is not None:
            yield self.search_input
        yield self.option_list
        if self._footer_text:
            yield Static(self._footer_text, classes="modal-footer")
