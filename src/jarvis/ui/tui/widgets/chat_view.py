"""
Chat View Widget — Displays conversation history, tool calls, and streaming output.
Professional layout with improved spacing, hierarchy, and visual clarity.
"""

from __future__ import annotations

import re
import time

from rich.markdown import Markdown
from rich.text import Text
from textual import events
from textual.containers import VerticalScroll
from textual.message import Message as TextualMessage
from textual.widgets import Static

from jarvis.ui.tui.utils import format_tool_name

THINK_TAG_OPEN_RE = re.compile(r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>", re.IGNORECASE)
THINK_TAG_CLOSE_RE = re.compile(r"</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>", re.IGNORECASE)
THINK_REGEX = re.compile(
    r"<(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>(.*?)</(?:think|thought|reasoning)(?::[a-zA-Z0-9_-]+)?>",
    re.DOTALL | re.IGNORECASE,
)



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
            cleaned = content.strip()
            while cleaned.startswith("❌"):
                cleaned = cleaned[1:].strip()
            while cleaned.lower().startswith("error:"):
                cleaned = cleaned[6:].strip()
            if not cleaned:
                cleaned = "Request interrupted or an unexpected error occurred."
            self.update(Text(f"❌ Error: {cleaned}", style="bold #fca5a5"))
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


class ThoughtWidget(Static):
    """Clickable and collapsible thought/reasoning widget.

    Displays 'Thinking...' with an animated indicator while active.
    When finished, displays 'Thought (n seconds)' or 'Thought (450ms)'.
    Clicking toggles between expanded and collapsed states.
    """

    DEFAULT_CSS = """
    ThoughtWidget {
        height: auto;
        margin: 0 0 0 2;
        padding: 0;
    }

    .thought-header {
        color: #d97706;
        height: 1;
    }

    .thought-header:hover {
        color: #fbbf24;
        text-style: underline;
    }

    .thought-content-block {
        color: #a3a3a3;
        padding: 0 0 0 2;
        margin: 0;
        display: none;
    }

    .thought-content-block.expanded {
        display: block;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.raw_thought: str = ""
        self._is_finished: bool = False
        self._start_time: float = time.time()
        self._elapsed_str: str = ""
        self._expanded: bool = False
        self._animation_frame: int = 0
        self._timer = None

        self.header_widget = Static(self._format_header(), classes="thought-header")
        self.content_widget = Static("", classes="thought-content-block")

    def _format_header(self) -> Text:
        t = Text()
        if not self._is_finished:
            dots = "." * ((self._animation_frame % 3) + 1)
            t.append("⟡ ", style="bold #d97706")
            t.append(f"Thinking{dots}", style="italic #d97706")
        else:
            indicator = "▾ " if self._expanded else "▸ "
            t.append(indicator, style="dim #a3a3a3")
            if self._elapsed_str:
                t.append(f"Thought ({self._elapsed_str})", style="italic #a3a3a3")
            else:
                t.append("Thought", style="italic #a3a3a3")
        return t

    def compose(self):
        yield self.header_widget
        yield self.content_widget

    def on_mount(self) -> None:
        if not self._is_finished:
            self._timer = self.set_interval(0.3, self._tick_animation)

    def _tick_animation(self) -> None:
        if not self._is_finished:
            self._animation_frame += 1
            self.header_widget.update(self._format_header())

    def append_chunk(self, chunk: str) -> None:
        self.raw_thought += chunk
        self._update_content_display()

    def set_content(self, thought_text: str, elapsed_str: str = "") -> None:
        self.raw_thought = thought_text
        if elapsed_str:
            self._elapsed_str = elapsed_str
            self.finish(elapsed_str)
        else:
            self._update_content_display()

    def _update_content_display(self) -> None:
        if not self.raw_thought.strip():
            self.content_widget.update(Text("", style="#a3a3a3"))
            return
        try:
            self.content_widget.update(Markdown(self.raw_thought))
        except Exception:
            self.content_widget.update(Text(self.raw_thought, style="#a3a3a3"))

    def finish(self, elapsed_str: str = "") -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._is_finished = True

        if not elapsed_str:
            elapsed = time.time() - self._start_time if self._start_time > 0 else 0
            if elapsed < 1.0:
                elapsed_str = f"{int(elapsed * 1000)}ms"
            elif elapsed < 10.0:
                elapsed_str = f"{elapsed:.1f}s"
            else:
                elapsed_str = f"{round(elapsed)}s"

        self._elapsed_str = elapsed_str
        self.header_widget.update(self._format_header())
        self._update_content_display()

    def toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self.content_widget.add_class("expanded")
        else:
            self.content_widget.remove_class("expanded")
        self.header_widget.update(self._format_header())

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.toggle_expanded()

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None


class ToolCallWidget(Static):
    """Clickable tool call widget displaying '▸ ToolName description' in small grey text.
    
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
        indicator = "▾ " if self._expanded else "▸ "
        t = Text()
        t.append(indicator, style="dim #737373")
        t.append(f"{formatted_name}", style="dim #a3a3a3")
        if self.args_str:
            t.append(f" {self.args_str}", style="dim #737373")
        return t

    def compose(self):
        yield self.header_widget
        yield self.output_widget

    def set_output(self, output_text: str) -> None:
        self.result_text = output_text
        display_text = output_text
        if len(display_text) > 10000:
            display_text = display_text[:10000] + "\n... (output truncated)"
        t = Text()
        t.append(f"↳ {display_text}", style="italic #737373")
        self.output_widget.update(t)
        self.header_widget.update(self._format_header())

    def toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            if not self.result_text:
                t = Text()
                t.append("↳ (executing tool...)", style="italic #525252")
                self.output_widget.update(t)
            self.output_widget.add_class("expanded")
        else:
            self.output_widget.remove_class("expanded")
        self.header_widget.update(self._format_header())

    def on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()
        self.toggle_expanded()


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
        self._current_thought_widget: ThoughtWidget | None = None
        self._last_tool_widget: ToolCallWidget | None = None
        self._start_time: float = 0.0
        self._has_messages: bool = False
        self._loading_timer = None
        self._loading_frame: int = 0
        self._is_first_chunk: bool = False
        self._message_counter: int = 0  # Sequential index for user messages
        self._in_think: bool = False
        self._stream_buffer: str = ""

    @property
    def has_messages(self) -> bool:
        return self._has_messages

    def clear_messages(self) -> None:
        self._stop_loading_timer()
        for child in list(self.children):
            child.remove()
        self._current_assistant_widget = None
        self._current_thought_widget = None
        self._last_tool_widget = None
        self._has_messages = False
        self._is_first_chunk = False
        self._message_counter = 0
        self._in_think = False
        self._stream_buffer = ""
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
        self._current_thought_widget = None
        self._last_tool_widget = None
        self._is_first_chunk = False
        self._in_think = False
        self._stream_buffer = ""

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
        if self._current_assistant_widget and self._is_first_chunk and not self._in_think:
            dots = "." * ((self._loading_frame % 3) + 1)
            self._loading_frame += 1
            self._current_assistant_widget.update_content(dots)

    def on_unmount(self) -> None:
        self._stop_loading_timer()

    def _is_at_bottom(self, threshold: float = 4.0) -> bool:
        """Return True if the user is currently scrolled at or near the bottom."""
        try:
            return (self.max_scroll_y - self.scroll_y) <= threshold
        except Exception:
            return True

    def _scroll_to_bottom_if_auto(self) -> None:
        """Auto-scroll to the bottom only if the user is currently at the bottom."""
        if self._is_at_bottom():
            self.scroll_end(animate=False)

    def add_user_message(self, text: str) -> None:
        self._stop_loading_timer()
        self._mark_has_messages()
        idx = self._message_counter
        self._message_counter += 1
        msg = MessageWidget(content=text, role="user", message_index=idx)
        self.mount(msg)
        self.scroll_end(animate=False)
        self._current_assistant_widget = None
        self._current_thought_widget = None
        self._in_think = False
        self._stream_buffer = ""

    def add_thought(self, content: str = "", duration_ms: str = "407ms") -> ThoughtWidget:
        self._mark_has_messages()
        tw = ThoughtWidget()
        tw.set_content(content, elapsed_str=duration_ms)
        self.mount(tw)
        self.scroll_end(animate=False)
        return tw

    def _start_thought(self) -> ThoughtWidget:
        self._stop_loading_timer()
        tw = ThoughtWidget()
        self.mount(tw)
        self._current_thought_widget = tw
        self._scroll_to_bottom_if_auto()
        return tw

    def _append_thought_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        if self._current_thought_widget is None:
            self._start_thought()
        if self._current_thought_widget:
            self._current_thought_widget.append_chunk(chunk)
        self._scroll_to_bottom_if_auto()

    def _finish_thought(self) -> None:
        if self._current_thought_widget is not None:
            self._current_thought_widget.finish()
            self._current_thought_widget = None

    def _append_text_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        self._mark_has_messages()
        if self._current_assistant_widget is None:
            msg = MessageWidget(content=chunk, role="assistant")
            self.mount(msg)
            self._current_assistant_widget = msg
            self._is_first_chunk = False
            self._stop_loading_timer()
        else:
            new_content = self._current_assistant_widget.raw_content + chunk
            self._current_assistant_widget.update_content(new_content)
        self._scroll_to_bottom_if_auto()

    def _flush_stream_buffer(self) -> None:
        if not self._stream_buffer:
            return
        buf = self._stream_buffer
        self._stream_buffer = ""
        if self._in_think:
            buf = THINK_TAG_CLOSE_RE.sub("", buf).rstrip()
            if buf:
                self._append_thought_chunk(buf)
            self._finish_thought()
            self._in_think = False
        else:
            buf = THINK_TAG_OPEN_RE.sub("", buf)
            if buf:
                self._append_text_chunk(buf)

    def add_tool_call(self, tool_name: str, args_str: str) -> ToolCallWidget:
        self._stop_loading_timer()
        self._flush_stream_buffer()
        self._finish_thought()
        self._current_assistant_widget = None

        tool_w = ToolCallWidget(tool_name=tool_name, args_str=args_str)
        self.mount(tool_w)
        self._last_tool_widget = tool_w
        self._scroll_to_bottom_if_auto()
        return tool_w

    def add_tool_output(self, output_text: str = "no output") -> None:
        self._stop_loading_timer()
        if self._last_tool_widget is not None:
            self._last_tool_widget.set_output(output_text)
        else:
            tool_w = ToolCallWidget(tool_name="tool", args_str="")
            tool_w.set_output(output_text)
            self.mount(tool_w)
            self._last_tool_widget = tool_w

        self._scroll_to_bottom_if_auto()

    def add_error_message(self, text: str) -> None:
        self._stop_loading_timer()
        self._flush_stream_buffer()
        self._finish_thought()
        self._current_assistant_widget = None
        msg = MessageWidget(content=text, role="error")
        self.mount(msg)
        self._scroll_to_bottom_if_auto()

    def start_assistant_stream(self) -> None:
        self._mark_has_messages()
        self._start_time = time.time()
        self._loading_frame = 0
        self._is_first_chunk = True
        self._in_think = False
        self._stream_buffer = ""
        self._current_assistant_widget = None
        self._current_thought_widget = None
        self.scroll_end(animate=False)

    def append_assistant_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        self._mark_has_messages()
        if self._start_time == 0.0:
            self._start_time = time.time()

        self._stream_buffer += chunk

        while self._stream_buffer:
            if not self._in_think:
                m = THINK_TAG_OPEN_RE.search(self._stream_buffer)
                if m:
                    before = self._stream_buffer[:m.start()]
                    if before:
                        self._append_text_chunk(before)
                    self._stream_buffer = self._stream_buffer[m.end():]
                    self._in_think = True
                    self._start_thought()
                else:
                    # Check if buffer ends with a potential opening tag prefix (e.g. "<th", "<think:61")
                    m_partial = re.search(r"<[a-zA-Z0-9_:-]*$", self._stream_buffer)
                    if m_partial:
                        prefix = m_partial.group(0).lower()
                        possible_tags = ("<think", "<thought", "<reasoning")
                        if any(t.startswith(prefix) or prefix.startswith(t) for t in possible_tags):
                            safe_text = self._stream_buffer[:m_partial.start()]
                            self._stream_buffer = self._stream_buffer[m_partial.start():]
                            if safe_text:
                                self._append_text_chunk(safe_text)
                            break
                    safe_text = self._stream_buffer
                    self._stream_buffer = ""
                    if safe_text:
                        self._append_text_chunk(safe_text)
                    break
            else:
                m = THINK_TAG_CLOSE_RE.search(self._stream_buffer)
                if m:
                    thought_before = self._stream_buffer[:m.start()]
                    if thought_before:
                        self._append_thought_chunk(thought_before)
                    self._stream_buffer = self._stream_buffer[m.end():]
                    self._in_think = False
                    self._finish_thought()
                else:
                    # Check if buffer ends with a potential closing tag prefix (e.g. "</th", "</think:61")
                    m_partial = re.search(r"</[a-zA-Z0-9_:-]*$", self._stream_buffer)
                    if m_partial:
                        prefix = m_partial.group(0).lower()
                        possible_tags = ("</think", "</thought", "</reasoning")
                        if any(t.startswith(prefix) or prefix.startswith(t) for t in possible_tags):
                            safe_thought = self._stream_buffer[:m_partial.start()]
                            self._stream_buffer = self._stream_buffer[m_partial.start():]
                            if safe_thought:
                                self._append_thought_chunk(safe_thought)
                            break
                    safe_thought = self._stream_buffer
                    self._stream_buffer = ""
                    if safe_thought:
                        self._append_thought_chunk(safe_thought)
                    break

    def update_assistant_stream(self, text: str) -> None:
        self.append_assistant_chunk(text)

    def finish_assistant_stream(
        self, mode: str = "", model_name: str = ""
    ) -> None:
        self._stop_loading_timer()
        self._flush_stream_buffer()
        self._finish_thought()

        elapsed_sec = time.time() - self._start_time if self._start_time > 0 else 0
        elapsed_str = f"{elapsed_sec:.1f}s"
        footer = AssistantFooterWidget(mode=mode, model=model_name, elapsed=elapsed_str)
        self.mount(footer)
        self._current_assistant_widget = None
        self._current_thought_widget = None
        self._start_time = 0.0
        self._scroll_to_bottom_if_auto()

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
                    thoughts = THINK_REGEX.findall(content)
                    cleaned_content = THINK_REGEX.sub("", content).strip()
                    for thought_text in thoughts:
                        thought_text = thought_text.strip()
                        if thought_text:
                            tw = ThoughtWidget()
                            tw.set_content(thought_text, elapsed_str="done")
                            self.mount(tw)

                    if cleaned_content:
                        m = MessageWidget(content=cleaned_content, role="assistant")
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
