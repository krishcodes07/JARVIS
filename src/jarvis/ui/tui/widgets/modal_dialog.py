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
from textual.geometry import Region
from textual.widgets import Input, OptionList, Static


class ModalOptionList(OptionList):
    """Custom OptionList for ModalDialog that keeps the highlighted item cleanly in view."""

    DEFAULT_CSS = """
    ModalOptionList {
        height: 1fr;
        min-height: 6;
        background: transparent;
        border: none;
    }
    """

    def scroll_to_highlight(self, top: bool = False) -> None:
        highlighted = self.highlighted
        if highlighted is None or not self.is_mounted:
            return

        self._update_lines()

        try:
            y = self._index_to_line[highlighted]
        except KeyError:
            return
        height = self._heights[highlighted]

        self.scroll_to_region(
            Region(0, y, self.scrollable_content_region.width, height),
            force=True,
            animate=False,
            top=top,
            immediate=True,
        )


class ModalDialog(Vertical):
    """A reusable modal dialog container with title bar, optional search, option list, and footer."""

    DEFAULT_CSS = """
    ModalDialog {
        background: $surface;
        border: none;
        padding: 1 2;
        max-height: 80%;
        max-width: 90%;
        min-height: 8;
    }

    ModalDialog .modal-title-bar {
        height: 1;
        layout: horizontal;
        margin-bottom: 1;
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
        background: transparent;
        border: solid #333333;
        margin: 0;
        color: #ffffff;
        height: 3;
        padding: 0 1;
    }

    ModalDialog .modal-search:focus {
        border: solid #3b82f6;
        background: transparent;
        color: #ffffff;
    }

    ModalDialog .modal-list-container {
        height: 1fr;
        margin-top: 0;
        background: transparent;
    }

    ModalDialog .modal-list {
        height: 1fr;
        min-height: 6;
        background: transparent;
        border: none;
        scrollbar-size: 0 0;
    }

    ModalDialog .modal-list > .option-list--option-highlighted {
        background: $primary 20%;
        color: $foreground;
        text-style: bold;
    }

    ModalDialog .modal-list > .option-list--option-hover {
        background: $primary 15%;
    }

    ModalDialog .modal-list > .option-list--option-highlighted-no-highlight {
        background: $primary 20%;
    }

    ModalDialog .modal-footer {
        height: 1;
        margin-top: 1;
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
        width: int | str = 62,
        height: int | str = "80%",
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
        self.option_list: OptionList = ModalOptionList(classes="modal-list")

        if self._show_search:
            self.search_input = Input(
                placeholder=self._search_placeholder,
                classes="modal-search",
            )

        self.styles.max_height = "80%"
        self.styles.max_width = "90%"

        if isinstance(self._dialog_width, (int, str)):
            self.styles.width = self._dialog_width
        if isinstance(self._dialog_height, (int, str)):
            self.styles.height = self._dialog_height
            if isinstance(self._dialog_height, int):
                self.styles.min_height = min(8, self._dialog_height)
            else:
                self.styles.min_height = 8
        else:
            self.styles.min_height = 8
        if self._border_style != "none":
            parts = self._border_style.split(" ", 1)
            if len(parts) == 2:
                self.styles.border = (parts[0], parts[1])  # type: ignore[assignment]
            elif len(parts) == 1:
                self.styles.border = (parts[0], "white")  # type: ignore[assignment]

    @property
    def title(self) -> str:
        return self._title_text


    def compose(self):
        with Horizontal(classes="modal-title-bar"):
            yield Static(self._title_text, classes="modal-title")
            yield Static("esc", classes="modal-esc")
        if self.search_input is not None:
            yield self.search_input
        with Vertical(classes="modal-list-container"):
            yield self.option_list
        if self._footer_text:
            yield Static(self._footer_text, classes="modal-footer")
