"""
Ask User Modal Screen — Interactive TUI dialog for gathering user decisions and input.

Supports single or multiple questions, numbered option selection, keyboard shortcuts,
and a fixed "Custom" option with an inline input field for typing freeform responses.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.text import Text
from textual import on
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

logger = logging.getLogger(__name__)


class AskUserModal(ModalScreen[dict[str, Any] | None]):
    """Modal dialog presenting questions and options to the user in the TUI."""

    DEFAULT_CSS = """
    AskUserModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.65);
    }

    #ask-user-dialog {
        background: #0e1018;
        border: solid #06b6d4;
        padding: 1 2;
        width: 72;
        height: auto;
        min-height: 18;
        max-height: 85%;
    }

    #ask-user-q-header {
        color: #06b6d4;
        text-style: bold;
        height: auto;
        margin-bottom: 1;
    }

    #ask-user-q-text {
        color: #ffffff;
        text-style: bold;
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }

    #ask-user-custom-container {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        display: none;
    }

    #ask-user-custom-container.active {
        display: block;
    }

    #ask-user-custom-input {
        background: #1e1e2e;
        border: solid #06b6d4;
        color: #ffffff;
        height: 3;
        padding: 0 1;
    }

    #ask-user-custom-input:focus {
        border: solid #8b5cf6;
    }
    """

    def __init__(
        self,
        questions: list[dict[str, Any]],
        title: str = "JARVIS Question",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.questions = questions or []
        self.current_idx = 0
        self.answers: dict[str, Any] = {}
        self.custom_mode = False

        self.dialog = ModalDialog(
            title="✦ JARVIS INQUIRY",
            dialog_id="ask-user-dialog",
            width=74,
            height=20,
            show_search=False,
            footer_text="↑↓ navigate   Enter select   1-9 quick pick   c custom   Esc skip",
            border_style="solid #06b6d4",
        )

        self.q_header_widget = Static("", id="ask-user-q-header")
        self.q_text_widget = Static("", id="ask-user-q-text")
        self.custom_input = Input(
            placeholder="Type your custom response and press Enter...",
            id="ask-user-custom-input",
        )
        self.custom_container = Vertical(self.custom_input, id="ask-user-custom-container")

    @property
    def option_list(self) -> OptionList:
        return self.dialog.option_list

    def compose(self):
        yield self.dialog

    def on_mount(self) -> None:
        # Insert custom input container below the option list inside dialog
        list_container = self.dialog.query_one(".modal-list-container")
        if list_container:
            self.dialog.mount(self.custom_container, after=list_container)

        self._render_current_question()

    def _render_current_question(self) -> None:
        """Render the question at self.current_idx."""
        if not self.questions or self.current_idx >= len(self.questions):
            self.dismiss(self.answers)
            return

        self.custom_mode = False
        self.custom_container.remove_class("active")
        self.custom_input.value = ""

        q = self.questions[self.current_idx]
        total_q = len(self.questions)
        q_text = q.get("question", "What would you like to do?")
        header_title = q.get("header") or (f"Question {self.current_idx + 1} of {total_q}" if total_q > 1 else "Question")

        # Update modal title
        title_str = f"✦ JARVIS INQUIRY [{self.current_idx + 1}/{total_q}]" if total_q > 1 else "✦ JARVIS INQUIRY"
        self.dialog._title_text = title_str
        if hasattr(self.dialog, "title_widget") and self.dialog.title_widget:
            self.dialog.title_widget.update(title_str)

        # Populate option list
        self.option_list.clear_options()

        # Header item (question prompt)
        prompt_rich = Text(f" {header_title}\n {q_text}\n", style="bold #ffffff")
        self.option_list.add_option(Option(prompt_rich, disabled=True))

        # Add choices
        raw_options = q.get("options") or []
        for idx, opt in enumerate(raw_options, start=1):
            key_hint = f"[{idx}]" if idx <= 9 else "  "
            opt_text = Text()
            opt_text.append(f"  {key_hint} ", style="bold #06b6d4")
            opt_text.append(f"{opt}", style="#e5e7eb")
            self.option_list.add_option(Option(opt_text, id=f"opt_{idx - 1}"))

        # Add fixed Custom option
        custom_text = Text()
        custom_text.append("  [C] ✎ ", style="bold #d97706")
        custom_text.append("Custom: Type your own answer...", style="italic #f59e0b")
        self.option_list.add_option(Option(custom_text, id="custom_option"))

        self.option_list.highlighted = 1
        if self.is_mounted:
            try:
                self.option_list.focus()
            except Exception:
                pass

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = getattr(event, "option_id", None) or (
            event.option.id if getattr(event, "option", None) else None
        )

        if opt_id == "custom_option":
            self._activate_custom_input()
            return

        if opt_id and opt_id.startswith("opt_"):
            try:
                idx = int(opt_id.split("_")[1])
                q = self.questions[self.current_idx]
                opts = q.get("options", [])
                if 0 <= idx < len(opts):
                    selected_value = opts[idx]
                    self._record_answer(selected_value)
            except Exception as e:
                logger.warning("Error picking option: %s", e)

    def _activate_custom_input(self) -> None:
        """Activate the inline custom text input."""
        self.custom_mode = True
        self.custom_container.add_class("active")
        self.custom_input.focus()

    @on(Input.Submitted, "#ask-user-custom-input")
    def on_custom_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if not val:
            val = "(Custom response: blank)"
        self._record_answer(val)

    def _record_answer(self, answer: str) -> None:
        """Save answer for current question and proceed to next or finish."""
        q = self.questions[self.current_idx]
        q_key = q.get("question", f"question_{self.current_idx}")
        self.answers[q_key] = answer

        self.current_idx += 1
        if self.current_idx < len(self.questions):
            self._render_current_question()
        else:
            self.dismiss(self.answers)

    def key_escape(self) -> None:
        """Escape cancels or finishes with partial/empty answers."""
        if self.custom_mode:
            # Revert from custom input to option list
            self.custom_mode = False
            self.custom_container.remove_class("active")
            self.option_list.focus()
            return

        self.dismiss(self.answers if self.answers else None)

    def key_c(self) -> None:
        """Press 'c' to quickly trigger custom input."""
        if not self.custom_mode:
            self._activate_custom_input()

    def on_key(self, event: Any) -> None:
        """Handle numeric keys 1-9 for quick selection."""
        if self.custom_mode:
            return

        key = event.key
        if key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            num = int(key)
            if self.current_idx < len(self.questions):
                q = self.questions[self.current_idx]
                opts = q.get("options", [])
                if 1 <= num <= len(opts):
                    self._record_answer(opts[num - 1])
                    event.prevent_default()
                    event.stop()
