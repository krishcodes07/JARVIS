"""
Prompt Box Widget — Compact, professional input area.
Clean design with proper proportions and visual clarity.
"""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING

from rich.text import Text
from textual import events, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TextArea

if TYPE_CHECKING:
    from textual.widgets.text_area import EditResult

MOUSE_ESCAPE_PATTERN = re.compile(r"(?:\x1b|\^\[)?\[<\d+;\d+;\d+[mM]")


class PromptInputTextArea(TextArea):
    """Custom TextArea for PromptBoxWidget supporting Enter=Submit and Shift+Enter=Newline."""

    class Submitted(Message):
        """Posted when user submits prompt with Enter."""

        def __init__(self, input_control: PromptInputTextArea, value: str) -> None:
            super().__init__()
            self.input = input_control
            self.value = value

    @on(TextArea.Changed)
    def _on_text_changed(self) -> None:
        """Sanitize self.text live whenever text changes to eliminate mouse escape sequences."""
        if MOUSE_ESCAPE_PATTERN.search(self.text):
            cleaned = MOUSE_ESCAPE_PATTERN.sub("", self.text)
            if cleaned != self.text:
                self.load_text(cleaned)

    def insert(
        self,
        text: str,
        location: tuple[int, int] | None = None,
        *,
        maintain_selection_offset: bool = True,
    ) -> EditResult:
        """Filter out raw ANSI SGR mouse tracking escape codes before insertion."""
        cleaned = MOUSE_ESCAPE_PATTERN.sub("", text)
        return super().insert(
            cleaned,
            location=location,
            maintain_selection_offset=maintain_selection_offset,
        )

    async def _on_key(self, event: events.Key) -> None:
        # Ignore raw SGR mouse escape sequences delivered as key events
        char = getattr(event, "character", None)
        key = getattr(event, "key", None)
        if (isinstance(char, str) and MOUSE_ESCAPE_PATTERN.search(char)) or (
            isinstance(key, str) and MOUSE_ESCAPE_PATTERN.search(key)
        ):
            event.prevent_default()
            event.stop()
            return

        is_newline_key = (
            event.key in ("shift+enter", "alt+enter", "ctrl+enter")
            or (event.key == "enter" and (getattr(event, "shift", False) or getattr(event, "alt", False) or getattr(event, "ctrl", False)))
        )
        if is_newline_key:
            self.insert("\n")
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self, self.text))
        elif event.key == "backspace" and self.text == "":
            # Clear pasted attachment if input field is empty
            try:
                box = self.screen.query_one("#prompt-card")
                clear_fn = getattr(box, "clear_pasted_text", None)
                if clear_fn and getattr(box, "_pasted_text", ""):
                    clear_fn()
                    event.prevent_default()
                    event.stop()
                    return
            except Exception:
                pass
            await super()._on_key(event)
        else:
            await super()._on_key(event)


class PromptBoxWidget(Widget):
    """Compact prompt container with auto-expanding height and visual clarity."""

    DEFAULT_CSS = """
    PromptBoxWidget {
        background: #1e1e1e;
        border: none;
        border-left: tall #3b82f6;
        height: auto;
        margin: 0 1 0 1;
        padding: 1 2 1 2;
    }

    #prompt-input-row {
        height: auto;
        min-height: 1;
        layout: horizontal;
        margin: 0 0 1 0;
    }

    #prefix-label {
        display: none;
        color: #ffffff;
        height: auto;
        width: auto;
        margin: 0 1 0 0;
        padding: 0;
    }

    #prefix-label.visible {
        display: block;
    }

    #paste-badge {
        display: none;
        background: #f97316;
        color: #ffffff;
        text-style: bold;
        padding: 0 1;
        margin: 0 1 0 0;
        height: auto;
        width: auto;
    }

    #paste-badge.visible {
        display: block;
    }

    #prompt-input-field {
        width: 1fr;
        height: 1;
        min-height: 1;
        max-height: 8;
        background: transparent !important;
        border: none !important;
        outline: none !important;
        color: #ffffff;
        padding: 0 !important;
        margin: 0 !important;
        scrollbar-size-vertical: 0;
        scrollbar-size-horizontal: 0;
    }

    #prompt-input-field:focus {
        background: transparent !important;
        border: none !important;
        outline: none !important;
    }

    #prompt-input-field > .text-area--cursor-line {
        background: transparent !important;
    }

    #prompt-input-field > .text-area--text {
        background: transparent !important;
    }

    #mic-button {
        width: 4;
        min-width: 4;
        height: 1;
        border: none;
        background: transparent;
        color: #60a5fa;
        content-align: center middle;
        padding: 0;
        margin: 0 0 0 1;
    }

    #mic-button:hover {
        color: #3b82f6;
        text-style: bold;
    }

    #mic-button.listening {
        color: #ef4444;
        text-style: bold;
    }

    #badge-line {
        height: 1;
        margin: 0;
        padding: 0;
        color: #a3a3a3;
    }

    #hint-line {
        display: none;
        height: 0;
        margin: 0;
        padding: 0;
    }

    #hint-line.hidden {
        display: none;
        height: 0;
        margin: 0;
        padding: 0;
    }
    """

    def __init__(
        self,
        mode: str = "Build",
        model: str = "Claude 3.5 Sonnet",
        provider: str = "Anthropic",
        reasoning: str = "extended",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.mode = mode
        self.model = model
        self.provider = provider
        self.reasoning = reasoning
        self._prefix_text: str = ""
        self._pasted_text: str = ""
        self._last_known_text: str = ""
        self._default_placeholder = 'Ask anything... "Fix broken tests"'
        self.prefix_label = Static("", id="prefix-label")
        self.paste_badge = Static("", id="paste-badge")
        self.input_field = PromptInputTextArea(
            placeholder=self._default_placeholder,
            show_line_numbers=False,
            soft_wrap=True,
            id="prompt-input-field",
        )
        self.input_field.tab_behavior = "focus"
        self.input_field.highlight_cursor_line = False
        self.input_field.show_vertical_scrollbar = False
        self.mic_button = Static("⭕", id="mic-button")
        self.badge_widget = Static(id="badge-line")
        self.hint_widget = Static(id="hint-line")

    def compose(self):
        with Horizontal(id="prompt-input-row"):
            yield self.prefix_label
            yield self.paste_badge
            yield self.input_field
            yield self.mic_button
        yield self.badge_widget
        yield self.hint_widget

    def update_input_height(self) -> None:
        if not self.is_mounted:
            return
        wrapped_lines = self.input_field.wrapped_document.height
        target_h = max(1, min(8, wrapped_lines))
        self.input_field.styles.height = target_h

    def insert_text(self, text: str) -> None:
        """Insert text into the prompt input field at the current cursor position."""
        if not text:
            return
        self.input_field.insert(text)
        self.input_field.focus()
        self._last_known_text = self.input_field.text
        self.update_input_height()

    def clear_pasted_text(self) -> None:
        pasted_was_present = bool(self._pasted_text)
        prefix = self._prefix_text
        self._pasted_text = ""
        self._prefix_text = ""
        self._last_known_text = ""
        self.input_field.placeholder = self._default_placeholder
        if self.is_mounted:
            self.paste_badge.remove_class("visible")
            self.paste_badge.update("")
            self.prefix_label.remove_class("visible")
            self.prefix_label.update("")
        if pasted_was_present and prefix:
            self.input_field.load_text(prefix)
            lines = prefix.split("\n")
            last_row = max(0, len(lines) - 1)
            last_col = len(lines[last_row]) if lines else 0
            with contextlib.suppress(Exception):
                self.input_field.move_cursor((last_row, last_col))
            self.update_input_height()

    @on(TextArea.Changed, "#prompt-input-field")
    def on_text_changed(self, event: TextArea.Changed | None = None) -> None:
        self.update_input_height()
        val = self.input_field.text

        if not self._pasted_text:
            inserted_text = val
            old_txt = self._last_known_text
            if old_txt and val.startswith(old_txt):
                inserted_text = val[len(old_txt):]

            if len(inserted_text) > 200 or len(inserted_text.splitlines()) >= 4:
                prefix = val[:len(val) - len(inserted_text)] if val.endswith(inserted_text) else old_txt
                self._prefix_text = prefix
                self._pasted_text = inserted_text
                n_lines = len(inserted_text.splitlines())
                badge_str = f"[Pasted ~{n_lines} lines]" if n_lines > 1 else f"[Pasted ~{len(inserted_text)} chars]"

                if prefix and self.is_mounted:
                    self.prefix_label.update(prefix)
                    self.prefix_label.add_class("visible")
                elif self.is_mounted:
                    self.prefix_label.remove_class("visible")

                if self.is_mounted:
                    self.paste_badge.update(badge_str)
                    self.paste_badge.add_class("visible")

                self.input_field.placeholder = ""
                self.input_field.load_text("")
                self._last_known_text = ""
                self.update_input_height()
                return

        self._last_known_text = val

    def set_listening_state(self, listening: bool) -> None:
        if listening:
            self.input_field.placeholder = "Listening... speak now"
            self.mic_button.update("🔴")
            self.mic_button.add_class("listening")
        else:
            self.input_field.placeholder = "" if (self._pasted_text or self._prefix_text) else self._default_placeholder
            self.mic_button.update("⭕")
            self.mic_button.remove_class("listening")

    def on_mount(self) -> None:
        self.update_badges(self.mode, self.model, self.provider, self.reasoning)
        self.update_hints()
        self.hint_widget.add_class("hidden")

    def update_badges(
        self,
        mode: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        reasoning: str | None = None,
    ) -> None:
        if mode is not None:
            self.mode = mode
        if model is not None:
            self.model = model
        if provider is not None:
            self.provider = provider
        if reasoning is not None:
            self.reasoning = reasoning

        txt = Text()
        txt.append(f"{self.model}", style="bold #ffffff")
        txt.append(" · ", style="dim #737373")
        txt.append(f"{self.provider}", style="dim #a3a3a3")

        if self.is_mounted:
            self.badge_widget.update(txt)

    def update_hints(self) -> None:
        txt = Text()
        txt.append("enter ", style="bold #4f9eff")
        txt.append("submit  ", style="dim #8ba1c0")
        txt.append("shift+enter ", style="bold #4f9eff")
        txt.append("newline  ", style="dim #8ba1c0")
        txt.append("esc ", style="bold #4f9eff")
        txt.append("clear", style="dim #8ba1c0")

        if self.is_mounted:
            self.hint_widget.update(txt)

    def show_hints(self) -> None:
        self.hint_widget.remove_class("hidden")

    def hide_hints(self) -> None:
        self.hint_widget.add_class("hidden")

    @property
    def text(self) -> str:
        input_txt = self.input_field.text
        parts = []
        if self._prefix_text:
            parts.append(self._prefix_text)
        if self._pasted_text:
            parts.append(self._pasted_text)
        if input_txt:
            parts.append(input_txt)
        return "\n\n".join(parts).strip() if parts else ""

    @text.setter
    def text(self, val: str) -> None:
        if len(val) > 200 or len(val.splitlines()) >= 4:
            self._prefix_text = ""
            self._pasted_text = val
            n_lines = len(val.splitlines())
            badge_str = f"[Pasted ~{n_lines} lines]" if n_lines > 1 else f"[Pasted ~{len(val)} chars]"
            if self.is_mounted:
                self.prefix_label.remove_class("visible")
                self.paste_badge.update(badge_str)
                self.paste_badge.add_class("visible")
            self.input_field.placeholder = ""
            self.input_field.load_text("")
            self._last_known_text = ""
        else:
            self.clear_pasted_text()
            self.input_field.load_text(val)
            self._last_known_text = val

        lines = val.split("\n")
        last_row = max(0, len(lines) - 1)
        last_col = len(lines[last_row]) if lines else 0
        with contextlib.suppress(Exception):
            self.input_field.move_cursor((last_row, last_col))
        self.update_input_height()

    def clear(self) -> None:
        self._prefix_text = ""
        self._pasted_text = ""
        self._last_known_text = ""
        self.input_field.placeholder = self._default_placeholder
        if self.is_mounted:
            self.paste_badge.remove_class("visible")
            self.paste_badge.update("")
            self.prefix_label.remove_class("visible")
            self.prefix_label.update("")
        self.input_field.load_text("")
        self.update_input_height()
