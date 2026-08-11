"""
Chat View Widget — Displays conversation history, tool calls, and streaming output.
Professional layout with improved spacing, hierarchy, and visual clarity.
"""

from __future__ import annotations

import time

from rich.markdown import Markdown
from rich.text import Text
from textual import events, on
from textual.containers import VerticalScroll
from textual.message import Message as TextualMessage
from textual.widgets import Static

from jarvis.ui.tui.utils import format_tool_name, truncate_text


class MessageWidget(Static):
    """A single chat message or event in the feed with improved spacing.

    User messages are clickable — clicking one posts an ``ActionRequested``
    event so the screen can open the Message Actions modal.
    """

    class ActionRequested(TextualMessage):
        """Posted when a user message is clicked to open message actions."""

        def __init__(
            self,
            widget: MessageWidget,
            message_text: str,
            message_index: int,
        ) -> None:
            super().__init__()
            self.widget = widget
            self.message_text = message_text
            self.message_index = message_index

    DEFAULT_CSS = """
    MessageWidget.chat-message-user {
        /* subtle hover highlight so user knows it's clickable */
    }
    MessageWidget.chat-message-user:hover {
        background: #ffffff 8%;
    }
    """

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        message_index: int = -1,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.raw_content = content
        self.message_index: int = message_index
        self._apply_content(content)

    def _apply_content(self, content: str) -> None:
        self.raw_content = content
        if self.role == "user":
            self.add_class("chat-message-user")
            self.update(Text(content, style="#f8fafc"))
        elif self.role == "thought":
            self.add_class("chat-thought-block")
            self.update(Text(f"+ Thought: {content}", style="bold #ff9a4f"))
        elif self.role == "error":
            self.add_class("chat-error-message")
            self.update(Text(f"❌ Error: {content}", style="bold #fca5a5"))
        else:
            self.add_class("chat-message-jarvis")
            if content:
                try:
                    self.update(Markdown(content))
                except Exception:
                    self.update(Text(content, style="#f8fafc"))

    def update_content(self, new_content: str) -> None:
        self._apply_content(new_content)

    def on_click(self, event: events.Click) -> None:
        """Open message actions modal when a user message is clicked."""
        if self.role == "user" and self.message_index >= 0:
            event.stop()
            self.post_message(
                self.ActionRequested(
                    widget=self,
                    message_text=self.raw_content,
                    message_index=self.message_index,
                )
            )


class ToolCallWidget(Static):
    """Clickable tool call widget displaying '→ ToolName description' in small grey text.
    
    Clicking toggles displaying the tool output directly below.
    """

    DEFAULT_CSS = """
    ToolCallWidget {
        height: auto;
        margin: 0 0 0 2;
        padding: 0;
    }

    .tool-header {
        color: #a3a3a3;
        height: 1;
    }

    .tool-header:hover {
        color: #ffffff;
        text-style: underline;
    }

    .tool-output-block {
        color: #737373;
        padding: 0 0 0 2;
        margin: 0;
        display: none;
    }

    .tool-output-block.expanded {
        display: block;
    }
    """

    def __init__(self, tool_name: str, args_str: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args_str = args_str
        self.result_text: str = ""
        self._expanded: bool = False

        self.header_widget = Static(self._format_header(), classes="tool-header")
        self.output_widget = Static("", classes="tool-output-block")

    def _format_header(self) -> Text:
        formatted_name = format_tool_name(self.tool_name)
        t = Text()
        t.append("→ ", style="dim #737373")
        t.append(f"{formatted_name}", style="dim #a3a3a3")
        if self.args_str:
            t.append(f" {self.args_str}", style="dim #737373")
        return t

    def compose(self):
        yield self.header_widget
        yield self.output_widget

    def set_output(self, output_text: str) -> None:
        self.result_text = output_text
        res = truncate_text(output_text, max_length=1000, ellipsis="\n... (truncated)")
        t = Text()
        t.append(f"↳ {res}", style="italic #737373")
        self.output_widget.update(t)

    def on_click(self, event: events.Click) -> None:
        if self.result_text:
            self._expanded = not self._expanded
            if self._expanded:
                self.output_widget.add_class("expanded")
            else:
                self.output_widget.remove_class("expanded")


class AssistantFooterWidget(Static):
    """Footer badge under assistant response with improved formatting."""

    def __init__(
        self,
        mode: str = "",
        model: str = "",
        elapsed: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.add_class("assistant-footer-badge")
        t = Text()
        t.append("✓ ", style="bold #10b981")
        if model:
            t.append(f"{model}", style="dim #94a3b8")
        if elapsed:
            if model:
                t.append(" • ", style="dim #475569")
            t.append(f"{elapsed}", style="dim #64748b")
        self.update(t)


class ChatViewWidget(VerticalScroll):
    """Scrollable chat container with improved spacing and visual hierarchy."""

    DEFAULT_CSS = """
    ChatViewWidget {
        height: 1fr;
        padding: 1 1 1 1;
        overflow-y: scroll;
        scrollbar-size-vertical: 1;
        scrollbar-color: #3b82f6 #1e1e1e;
        scrollbar-size-horizontal: 0;
        border: none;
        background: #000000;
    }

    ChatViewWidget.hidden {
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_assistant_widget: MessageWidget | None = None
        self._last_tool_widget: ToolCallWidget | None = None
        self._start_time: float = 0.0
        self._has_messages: bool = False
        self._loading_timer = None
        self._loading_frame: int = 0
        self._is_first_chunk: bool = False
        self._message_counter: int = 0  # Sequential index for user messages

    @property
    def has_messages(self) -> bool:
        return self._has_messages

    def clear_messages(self) -> None:
        self._stop_loading_timer()
        for child in list(self.children):
            child.remove()
        self._current_assistant_widget = None
        self._last_tool_widget = None
        self._has_messages = False
        self._is_first_chunk = False
        self._message_counter = 0
        self.add_class("hidden")

    def remove_messages_from_index(self, from_index: int) -> None:
        """Remove all widgets starting from the user message with *from_index*.

        This removes the targeted user message, its AI response, tool calls,
        footers, and ALL subsequent messages (user + assistant) after it.
        """
        self._stop_loading_timer()
        removing = False
        to_remove: list = []

        for child in list(self.children):
            if not removing:
                # Start removing when we hit the user message with the matching index
                if (
                    isinstance(child, MessageWidget)
                    and child.role == "user"
                    and child.message_index == from_index
                ):
                    removing = True
                    to_remove.append(child)
            else:
                to_remove.append(child)

        for widget in to_remove:
            widget.remove()

        remaining_children = [c for c in self.children if c not in to_remove]

        # Reset streaming state
        self._current_assistant_widget = None
        self._last_tool_widget = None
        self._is_first_chunk = False

        # Recalculate message counter from remaining user messages
        remaining_user_count = sum(
            1 for c in remaining_children
            if isinstance(c, MessageWidget) and c.role == "user"
        )
        self._message_counter = remaining_user_count

        # If no messages remain, show empty state
        if not any(
            isinstance(c, MessageWidget)
            for c in remaining_children
        ):
            self._has_messages = False
            self.add_class("hidden")
        else:
            self.scroll_end(animate=False)

    def _mark_has_messages(self) -> None:
        if not self._has_messages:
            self._has_messages = True
            self.remove_class("hidden")
            try:
                screen = self.screen
                if hasattr(screen, "on_first_message"):
                    screen.on_first_message()
            except Exception:
                pass

    def _stop_loading_timer(self) -> None:
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer = None

    def _update_loading_dots(self) -> None:
        if self._current_assistant_widget and self._is_first_chunk:
            dots = "." * ((self._loading_frame % 3) + 1)
            self._loading_frame += 1
            self._current_assistant_widget.update_content(dots)

    def on_unmount(self) -> None:
        self._stop_loading_timer()

    def add_user_message(self, text: str) -> None:
        self._stop_loading_timer()
        self._mark_has_messages()
        idx = self._message_counter
        self._message_counter += 1
        msg = MessageWidget(content=text, role="user", message_index=idx)
        self.mount(msg)
        self.scroll_end(animate=False)
        self._current_assistant_widget = None

    def add_thought(self, duration_ms: str = "407ms") -> None:
        msg = MessageWidget(content=duration_ms, role="thought")
        self.mount(msg)
        self.scroll_end(animate=False)

    def add_tool_call(self, tool_name: str, args_str: str) -> ToolCallWidget:
        self._stop_loading_timer()
        if self._current_assistant_widget is not None:
            if not self._current_assistant_widget.raw_content.strip() or self._is_first_chunk:
                self._current_assistant_widget.remove()
            self._current_assistant_widget = None
            self._is_first_chunk = False

        tool_w = ToolCallWidget(tool_name=tool_name, args_str=args_str)
        self.mount(tool_w)
        self._last_tool_widget = tool_w
        self.scroll_end(animate=False)
        return tool_w

    def add_tool_output(self, output_text: str = "no output") -> None:
        self._stop_loading_timer()
        if self._current_assistant_widget is not None:
            if not self._current_assistant_widget.raw_content.strip() or self._is_first_chunk:
                self._current_assistant_widget.remove()
            self._current_assistant_widget = None
            self._is_first_chunk = False

        if self._last_tool_widget is not None:
            self._last_tool_widget.set_output(output_text)
        else:
            tool_w = ToolCallWidget(tool_name="tool", args_str="")
            tool_w.set_output(output_text)
            self.mount(tool_w)
            self._last_tool_widget = tool_w

        self.scroll_end(animate=False)

    def add_error_message(self, text: str) -> None:
        self._stop_loading_timer()
        if self._current_assistant_widget is not None:
            if not self._current_assistant_widget.raw_content.strip() or self._is_first_chunk:
                self._current_assistant_widget.remove()
            self._current_assistant_widget = None
            self._is_first_chunk = False
        msg = MessageWidget(content=text, role="error")
        self.mount(msg)
        self.scroll_end(animate=False)

    def start_assistant_stream(self) -> MessageWidget | None:
        self._mark_has_messages()
        self._start_time = time.time()
        self._loading_frame = 0
        self._is_first_chunk = True

        msg = MessageWidget(content=".", role="assistant")
        self.mount(msg)
        self._current_assistant_widget = msg

        self._stop_loading_timer()
        self._loading_timer = self.set_interval(0.3, self._update_loading_dots)

        self.scroll_end(animate=False)
        return self._current_assistant_widget

    def append_assistant_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        self._mark_has_messages()
        if self._start_time == 0.0:
            self._start_time = time.time()

        if self._current_assistant_widget is None:
            msg = MessageWidget(content="", role="assistant")
            self.mount(msg)
            self._current_assistant_widget = msg
            self._is_first_chunk = False
            self._stop_loading_timer()
        elif self._is_first_chunk:
            self._is_first_chunk = False
            self._stop_loading_timer()
            self._current_assistant_widget.raw_content = ""

        new_content = self._current_assistant_widget.raw_content + chunk
        self._current_assistant_widget.update_content(new_content)
        self.scroll_end(animate=False)

    def update_assistant_stream(self, text: str) -> None:
        self.append_assistant_chunk(text)

    def finish_assistant_stream(
        self, mode: str = "", model_name: str = ""
    ) -> None:
        self._stop_loading_timer()
        if self._current_assistant_widget is not None and self._is_first_chunk:
            if not self._current_assistant_widget.raw_content.strip():
                self._current_assistant_widget.remove()
                self._current_assistant_widget = None
            self._is_first_chunk = False
        elapsed_sec = time.time() - self._start_time if self._start_time > 0 else 0
        elapsed_str = f"{elapsed_sec:.1f}s"
        footer = AssistantFooterWidget(mode=mode, model=model_name, elapsed=elapsed_str)
        self.mount(footer)
        self._current_assistant_widget = None
        self._start_time = 0.0
        self.scroll_end(animate=False)

    def load_session_history(self, messages: list[dict]) -> None:
        self.clear_messages()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system" or msg.get("_session_title"):
                continue
            if role == "user":
                if content:
                    self.add_user_message(content)
            elif role == "assistant":
                if content:
                    m = MessageWidget(content=content, role="assistant")
                    self.mount(m)
                    saved_model = msg.get("model") or msg.get("model_name") or "JARVIS"
                    footer = AssistantFooterWidget(mode="", model=saved_model, elapsed="")
                    self.mount(footer)
            elif role in ("tool", "tool_call", "tool_result"):
                tool_name = msg.get("tool_name") or msg.get("name") or "tool"
                args_str = msg.get("args_str") or ""
                tool_w = self.add_tool_call(tool_name, args_str)
                if content:
                    tool_w.set_output(content)
        if self._has_messages:
            self.scroll_end(animate=False)
