"""
Main Screen — Primary workspace view for JARVIS Terminal UI.
OpenCode/ClaudeCode layout: header hides on first message, compact prompt at bottom.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from textual import events, on, work
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual.widgets import Button, Input, TextArea
from textual.worker import get_current_worker

from jarvis.core.paths import get_sessions_dir
from jarvis.core.snapshot import FileSnapshotManager
from jarvis.providers.models_dev import (
    format_env_var_label,
    get_model_context_limit,
    get_provider_env_vars,
)
from jarvis.ui.tui.screens.modals import (
    ApiKeyModal,
    ConfigModal,
    ConnectModal,
    DebugModal,
    EffortModal,
    HelpModal,
    MCPModal,
    MessageActionsModal,
    ModelModal,
    SessionModal,
    ThemeModal,
)
from jarvis.ui.tui.utils import copy_to_clipboard
from jarvis.ui.tui.voice_controller import VoiceSessionController
from jarvis.ui.tui.widgets import (
    ChatViewWidget,
    CommandPopoverWidget,
    HeaderWidget,
    MessageWidget,
    NotificationToast,
    PromptBoxWidget,
    PromptInputTextArea,
    StatusBarWidget,
)

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class MainScreen(Screen):
    """Main workspace screen for JARVIS TUI."""

    DEFAULT_CSS = """
    MainScreen {
        layers: default overlay;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+n", "new_session", "New Session", show=False),
        Binding("ctrl+m", "open_models", "Models", show=False),
        Binding("ctrl+s", "open_sessions", "Sessions", show=False),
        Binding("ctrl+h", "open_help", "Help", show=False),
        Binding("ctrl+l", "clear_screen", "Clear", show=False),
        Binding("alt+v", "toggle_voice", "Voice Mode", show=False),
    ]

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.voice_controller = VoiceSessionController(engine=self.engine)
        self.snapshot_manager = FileSnapshotManager()
        self.header = HeaderWidget(id="header-container")
        self.chat_view = ChatViewWidget(id="chat-scroll")
        self.popover = CommandPopoverWidget(id="command-popover")
        self.prompt_box = PromptBoxWidget(id="prompt-card")
        self.status_bar = StatusBarWidget(id="status-bar")
        self.toast = NotificationToast(id="notification-toast")
        self._is_generating: bool = False
        self._current_worker = None
        self._prompt_history: list[str] = []
        self._history_index: int = -1
        self._git_checkpoints: dict[int, dict[str, Any]] = {}

    @property
    def _current_session_id(self) -> str:
        if self.engine and self.engine.session and self.engine.session.session_id:
            return self.engine.session.session_id
        return "default"

    def compose(self):
        yield self.header
        yield self.chat_view
        yield self.popover
        yield self.prompt_box
        yield self.status_bar
        yield self.toast

    def show_toast(
        self,
        message: str,
        title: str = "Notification",
        style: Literal["info", "success", "warning", "error"] = "info",
        duration: float = 3.5,
    ) -> None:
        """Show a floating toast notification overlay."""
        self.toast.show_toast(message, title=title, style=style, duration=duration)

    def on_mount(self) -> None:
        import sys
        with contextlib.suppress(Exception):
            sys.stdout.write("\x1b[?1003l")
            sys.stdout.flush()

        self.prompt_box.input_field.focus()
        self.update_engine_status()
        # Load current session history
        if self.engine and self.engine.session:
            self.load_session_history(self.engine.session.session_id)

        if not self.chat_view.has_messages:
            self.header.show_header()
            self.chat_view.clear_messages()
            self.prompt_box.show_hints()

        # Alert user if no LLM provider is connected
        if self.engine and self.engine.provider_manager and not self.engine.provider_manager.has_connected_provider:
            self.show_toast(
                "No AI provider connected. Use /connect (or press Ctrl+A) to connect a provider.",
                title="No Provider Connected",
                style="warning",
                duration=6.0,
            )

    def on_first_message(self) -> None:
        """Called by ChatViewWidget when the first message appears. Hide header and hints."""
        self.header.hide_header()
        self.prompt_box.hide_hints()

    def update_engine_status(self) -> None:
        if self.engine and self.engine.config:
            c = self.engine.config
            from jarvis.providers.models_dev import (
                is_reasoning_model,
                has_configurable_reasoning,
                is_only_thinking_model,
                get_model_effort_values,
            )
            model = c.provider.model
            provider = c.provider.active

            reasoning_badge = "off"
            if is_only_thinking_model(model, provider):
                reasoning_badge = "inherent"
            elif not c.provider.thinking or (c.provider.reasoning_effort and c.provider.reasoning_effort.lower() == "none"):
                reasoning_badge = "off"
            elif c.provider.reasoning_effort:
                reasoning_badge = c.provider.reasoning_effort
            elif has_configurable_reasoning(model, provider):
                efforts = get_model_effort_values(model, provider)
                non_none = [e for e in efforts if e.lower() != "none"]
                reasoning_badge = non_none[0] if non_none else "on"
            elif is_reasoning_model(model, provider):
                reasoning_badge = "on"
            else:
                reasoning_badge = "off"

            self.prompt_box.update_badges(
                mode="",
                model=c.provider.model,
                provider=c.provider.active,
                reasoning=reasoning_badge,
            )
            if self.status_bar.context_tokens is not None:
                self._update_context_display()

    def _estimate_tokens(self, data: Any) -> int:
        """Estimate token count for string, message dict, or list of messages/texts."""
        if not data:
            return 0
        if isinstance(data, str):
            return max(1, int(len(data) / 4))
        if isinstance(data, dict):
            content = str(data.get("content", ""))
            return max(1, int(len(content) / 4))
        if isinstance(data, (list, tuple)):
            total_chars = 0
            for item in data:
                if isinstance(item, str):
                    total_chars += len(item)
                elif isinstance(item, dict):
                    total_chars += len(str(item.get("content", "")))
                elif hasattr(item, "content"):
                    total_chars += len(str(item.content))
            return max(0, int(total_chars / 4))
        return 0

    def _update_context_display(self, additional_response_tokens: int = 0) -> None:
        """Calculate and update context window usage in the status bar footer."""
        if not self.engine or not self.engine.config:
            return

        model_name = self.engine.config.provider.model
        provider_name = self.engine.config.provider.active
        context_limit = get_model_context_limit(model_name, provider_name)

        # Baseline system prompt + tools estimation (~1500 tokens default system context)
        baseline_tokens = 1500

        # Conversation history tokens
        history_tokens = 0
        if self.engine.memory_manager and self.engine.session:
            conv = self.engine.memory_manager.conversation
            if conv and hasattr(conv, "_buffers") and self.engine.session.session_id in conv._buffers:
                history_tokens = self._estimate_tokens(conv._buffers[self.engine.session.session_id])

        if history_tokens == 0 and hasattr(self.chat_view, "children"):
            msg_texts = [getattr(m, "raw_content", "") for m in self.chat_view.children if hasattr(m, "raw_content")]
            history_tokens = self._estimate_tokens(msg_texts)

        total_tokens = baseline_tokens + history_tokens + additional_response_tokens
        self.status_bar.set_context_usage(total_tokens, context_limit)


    def on_key(self, event: events.Key) -> None:
        # Handle Alt+V key shortcut to toggle voice mode cleanly without typing 'v'
        is_alt_v = (
            event.key in ("alt+v", "alt+V")
            or (getattr(event, "character", None) in ("v", "V") and getattr(event, "alt", False))
        )
        if is_alt_v:
            self.action_toggle_voice()
            event.prevent_default()
            event.stop()
            return

        # Handle Esc key to interrupt active generation stream or voice mode
        if event.key in ("escape", "esc") and (self._is_generating or self.voice_controller.is_active):
            if self._current_worker and not self._current_worker.is_finished:
                self._current_worker.cancel()
            self._is_generating = False
            self.voice_controller.stop()
            self.prompt_box.set_listening_state(False)
            self.status_bar.set_generating(False)

            event.prevent_default()
            event.stop()
            return

        val = self.prompt_box.text
        is_slash = val.startswith("/")

        if event.key == "tab":
            if not self.prompt_box.input_field.has_focus:
                with contextlib.suppress(Exception):
                    self.prompt_box.input_field.focus()

            if is_slash:
                selected_cmd = self.popover.get_selected_command()
                if selected_cmd:
                    # Autocomplete text into input box so user can add arguments
                    self.prompt_box.text = selected_cmd.name + " "
                    self.popover.hide()
                else:
                    self.popover.update_query(val)
            else:
                # Only insert '/' if prompt is empty; if user has already typed something, do nothing
                if not val.strip():
                    self.prompt_box.text = "/"
                    self.popover.update_query(self.prompt_box.text)

            event.prevent_default()
            event.stop()
            return

        if self.prompt_box.input_field.has_focus:
            is_popover_open = self.popover.styles.display == "block"
            if is_slash and is_popover_open and event.key in ("down", "pagedown"):
                self.popover.highlight_next()
                event.prevent_default()
                event.stop()
            elif is_slash and is_popover_open and event.key in ("up", "pageup"):
                self.popover.highlight_prev()
                event.prevent_default()
                event.stop()
            elif not is_popover_open and event.key in ("up", "pageup"):
                if self._prompt_history:
                    if self._history_index == -1:
                        self._history_index = len(self._prompt_history) - 1
                    elif self._history_index > 0:
                        self._history_index -= 1
                    self.prompt_box.text = self._prompt_history[self._history_index]
                    event.prevent_default()
                    event.stop()
            elif not is_popover_open and event.key in ("down", "pagedown"):
                if self._history_index != -1:
                    if self._history_index < len(self._prompt_history) - 1:
                        self._history_index += 1
                        self.prompt_box.text = self._prompt_history[self._history_index]
                    else:
                        self._history_index = -1
                        self.prompt_box.text = ""
                    event.prevent_default()
                    event.stop()

    @on(events.MouseScrollUp)
    def _on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.chat_view.scroll_relative(y=-3, animate=False)

    @on(events.MouseScrollDown)
    def _on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.chat_view.scroll_relative(y=3, animate=False)

    @on(TextArea.Changed, "#prompt-input-field")
    def on_prompt_text_changed(self, event: TextArea.Changed) -> None:
        val = self.prompt_box.text
        if val.startswith("/"):
            self.popover.update_query(val)
        else:
            self.popover.hide()

    def on_input_changed(self, event: Input.Changed) -> None:
        val = event.value
        if val.startswith("/"):
            self.popover.update_query(val)
        else:
            self.popover.hide()

    async def submit_prompt(self) -> None:
        user_input = self.prompt_box.text.strip()
        if not user_input:
            return

        selected_cmd = self.popover.get_selected_command()
        if user_input.startswith("/") and selected_cmd and len(user_input) < len(selected_cmd.name):
            user_input = selected_cmd.name

        # Stop active voice session cleanly if user submits typed prompt
        if self.voice_controller.is_active:
            self.voice_controller.stop()
            self.prompt_box.set_listening_state(False)

        if user_input.startswith("/"):
            self.prompt_box.clear()
            self.popover.hide()
            await self.handle_slash_command(user_input)
            return

        # Block chat query if no provider is connected
        if self.engine and self.engine.provider_manager and not self.engine.provider_manager.has_connected_provider:
            self.show_toast(
                "No AI provider connected. Use /connect (or press Ctrl+A) to connect a provider and start chatting.",
                title="No Provider Connected",
                style="warning",
                duration=5.0,
            )
            return

        if self._is_generating:
            return

        # Record non-slash user prompt in prompt history
        if not self._prompt_history or self._prompt_history[-1] != user_input:
            self._prompt_history.append(user_input)
        self._history_index = -1

        self.prompt_box.clear()
        self.popover.hide()

        self.chat_view.add_user_message(user_input)
        self.process_user_query(user_input)

    @on(PromptInputTextArea.Submitted)
    async def on_input_submitted(self, event: PromptInputTextArea.Submitted) -> None:
        await self.submit_prompt()

    @work(exclusive=True)
    async def process_user_query(self, query: str) -> None:
        if not self.engine:
            self.chat_view.add_error_message("JARVIS Engine not connected.")
            return

        # Save git checkpoint before processing (for revert file changes)
        msg_idx = self.chat_view._message_counter - 1
        self._save_git_checkpoint(msg_idx)

        self._current_worker = get_current_worker()
        self._is_generating = True
        self.status_bar.set_generating(True)

        self.chat_view.start_assistant_stream()

        async def on_tool_call(tool_name: str, tool_args: dict):
            args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
            self.chat_view.add_tool_call(tool_name, args_str)
            self.snapshot_manager.backup_tool_call(self._current_session_id, msg_idx, tool_name, tool_args)

        def on_tool_result(tool_name: str, result: str):
            self.chat_view.add_tool_output(result)

        async def approval_callback(tool_name: str, tool_args: dict) -> bool:
            args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
            self.chat_view.add_tool_call(f"APPROVAL REQUIRED: {tool_name}", args_str)
            return True

        try:
            async for chunk in self.engine.stream_chat(
                query,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
                approval_callback=approval_callback,
            ):
                self.chat_view.append_assistant_chunk(chunk)

            model_name = self.engine.last_used_model
            self.chat_view.finish_assistant_stream(mode="", model_name=model_name)
            self._update_context_display()

        except asyncio.CancelledError:
            logger.info("Chat stream cancelled by user.")
            model_name = self.engine.last_used_model if self.engine else "JARVIS"
            self.chat_view.finish_assistant_stream(mode="", model_name=model_name)
            self._update_context_display()
        except Exception as e:
            logger.exception("Error during chat processing")
            model_name = self.engine.last_used_model if self.engine else "JARVIS"
            self.chat_view.finish_assistant_stream(mode="", model_name=model_name)
            self.chat_view.add_error_message(f"Error: {e}")
            self._update_context_display()
        finally:
            self._is_generating = False
            self.status_bar.set_generating(False)

    @on(events.Click, "#mic-button")
    @on(Button.Pressed, "#mic-button")
    def on_mic_button_pressed(self) -> None:
        self.action_toggle_voice()

    def action_toggle_voice(self) -> None:
        if self.voice_controller.is_active:
            self.voice_controller.stop()
            self.prompt_box.set_listening_state(False)
            return

        self.run_voice_loop()

    @work(exclusive=True)
    async def run_voice_loop(self) -> None:
        ok, err = await self.voice_controller.ensure_initialized()
        if not ok:
            self.chat_view.add_error_message(err)
            self.voice_controller.stop()
            return

        self.voice_controller.is_active = True
        vm = self.engine.voice_manager  # type: ignore[union-attr]

        try:
            while self.voice_controller.is_active:
                self.prompt_box.set_listening_state(True)
                self.status_bar.set_generating(True)

                # 1. Capture speech from mic
                spoken_text = await vm.listen(cancel_checker=lambda: not self.voice_controller.is_active)


                if not self.voice_controller.is_active or spoken_text == "__CANCEL_VOICE_MODE__":
                    break

                if not spoken_text or not spoken_text.strip():
                    await asyncio.sleep(0.2)
                    continue

                user_query = spoken_text.strip()

                # Check auto_send_msg setting in voice config
                auto_send = True
                if self.engine and self.engine.config and hasattr(self.engine.config.voice, "auto_send_msg"):
                    auto_send = self.engine.config.voice.auto_send_msg

                if not auto_send:
                    # Insert transcribed text at current cursor location without sending
                    self.prompt_box.insert_text(user_query)
                    break

                # 2. Reset listening UI state while processing response
                self.prompt_box.set_listening_state(False)
                self.prompt_box.clear()
                self.chat_view.add_user_message(user_query)

                # 3. Stream LLM response
                model_name = self.engine.config.provider.model if (self.engine and self.engine.config) else "JARVIS"
                self.chat_view.start_assistant_stream()
                msg_idx = self.chat_view._message_counter - 1
                self._save_git_checkpoint(msg_idx)
                accumulated_response: list[str] = []

                async def on_tool_call(tool_name: str, tool_args: dict):
                    args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
                    self.chat_view.add_tool_call(tool_name, args_str)
                    self.snapshot_manager.backup_tool_call(self._current_session_id, msg_idx, tool_name, tool_args)

                def on_tool_result(tool_name: str, result: str):
                    self.chat_view.add_tool_output(result)

                async for chunk in self.engine.stream_chat(  # type: ignore[union-attr]
                    user_query,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                ):
                    if not self.voice_controller.is_active:
                        break
                    self.chat_view.append_assistant_chunk(chunk)
                    accumulated_response.append(chunk)

                self.chat_view.finish_assistant_stream(mode="", model_name=model_name)
                self._update_context_display()

                # 4. Synthesize and play response via TTS
                full_text = "".join(accumulated_response).strip()
                if full_text and self.voice_controller.is_active:
                    await vm.speak(full_text)

                # Short delay before automatically starting the next listening cycle
                await asyncio.sleep(0.3)

        except asyncio.CancelledError:
            logger.info("Voice loop cancelled.")
        except Exception as e:
            logger.exception("Voice mode error")
            self.chat_view.add_error_message(f"Voice Error: {e}")
        finally:
            self.voice_controller.stop()
            self.prompt_box.set_listening_state(False)
            self.status_bar.set_generating(False)

    async def handle_slash_command(self, cmd_str: str) -> None:
        parts = cmd_str.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        modal_handlers = {
            "/exit": lambda: self.app.exit(),
            "/quit": lambda: self.app.exit(),
            "/sessions": self.action_open_sessions,
            "/models": self.action_open_models,
            "/connect": self.action_open_connect,
            "/help": self.action_open_help,
            "/mcp": self.action_open_mcps,
            "/config": self.action_open_config,
            "/debug": self.action_open_debug,
            "/theme": self.action_open_theme,
            "/effort": self.action_open_effort,
        }

        if cmd in modal_handlers:
            if cmd == "/effort" and args:
                target_effort = args[0].lower()
                if self.engine and self.engine.config:
                    if target_effort == "none":
                        self.engine.config.provider.reasoning_effort = "none"
                        self.engine.config.provider.thinking = False
                    else:
                        self.engine.config.provider.reasoning_effort = target_effort
                        self.engine.config.provider.thinking = True
                    self.engine.config.save()
                    self.update_engine_status()
                    self.show_toast(f"Reasoning effort set to: {target_effort}", title="Effort Updated", style="success")
            elif cmd == "/theme" and args:
                target_theme = args[0].lower()
                from jarvis.ui.tui.theme import THEME_REGISTRY, apply_theme, get_theme
                if target_theme in THEME_REGISTRY:
                    theme_obj = get_theme(target_theme)
                    apply_theme(self.app, theme_obj.id)
                    if self.engine and self.engine.config:
                        self.engine.config.ui.tui.theme = theme_obj.id
                        self.engine.config.save()
                    self.show_toast(f"Switched TUI theme to: {theme_obj.display_name}", title="Theme Switched", style="success")
                else:
                    self.action_open_theme()
            else:
                modal_handlers[cmd]()
            return

        if cmd == "/new":
            new_session_id = "N/A"
            if self.engine:
                # Clean up empty session file before switching
                if self.engine.session:
                    old_sid = self.engine.session.session_id
                    await self.engine.session.end()
                    self._cleanup_empty_session(old_sid)
                from jarvis.core.session import Session
                self.engine.session = Session(engine=self.engine)
                new_session_id = self.engine.session.session_id

            self.chat_view.clear_messages()
            self.header.show_header()
            self.prompt_box.show_hints()
            self.status_bar.clear_context_usage()
            self._git_checkpoints.clear()
            self.show_toast(
                f"New conversation session created (ID: {new_session_id})",
                title="New Session",
                style="success",
            )

        elif cmd == "/clear":
            old_session_id = "N/A"
            if self.engine:
                if self.engine.session:
                    old_session_id = self.engine.session.session_id
                    await self.engine.session.end()
                if self.engine.memory_manager and self.engine.memory_manager.conversation:
                    await self.engine.memory_manager.conversation.delete(old_session_id)
                self.snapshot_manager.clear_session(old_session_id)
                from jarvis.core.session import Session
                self.engine.session = Session(engine=self.engine)

            self.chat_view.clear_messages()
            self.header.show_header()
            self.prompt_box.show_hints()
            self.status_bar.clear_context_usage()
            self.show_toast(
                f"Session deleted of ID {old_session_id}",
                title="Session Reset",
                style="info",
            )

        elif cmd == "/copy":
            last_text = ""
            for child in reversed(list(self.chat_view.children)):
                if getattr(child, "role", "") == "assistant" and hasattr(child, "raw_content"):
                    last_text = child.raw_content
                    break
            ok, msg = copy_to_clipboard(last_text)
            style_name = "success" if ok else ("warning" if last_text else "info")
            self.show_toast(msg, title="Clipboard", style=style_name)

        elif cmd == "/connect":
            self.action_open_connect()

        elif cmd == "/model":
            if args:
                model_name = args[0]
                if self.engine and self.engine.config:
                    self.engine.config.provider.model = model_name
                    self.engine.config.save()
                    self.update_engine_status()
                    self.chat_view.add_user_message(f"✓ Switched active model to: {model_name}")
            else:
                self.action_open_models()

        else:
            self.chat_view.add_error_message(f"Unknown command '{cmd}'. Type /help for available commands.")

    def load_session_history(self, session_id: str) -> None:
        filepath = get_sessions_dir() / f"{session_id}.json"
        if not filepath.exists():
            self.header.show_header()
            self.chat_view.clear_messages()
            self.prompt_box.show_hints()
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                messages = json.load(f)
                if isinstance(messages, list) and messages:
                    self.chat_view.load_session_history(messages)
                    if self.chat_view.has_messages:
                        self.header.hide_header()
                        self.prompt_box.hide_hints()
                        self._update_context_display()
                    else:
                        self.header.show_header()
                        self.chat_view.clear_messages()
                        self.prompt_box.show_hints()
                        self.status_bar.clear_context_usage()
                else:
                    self.header.show_header()
                    self.chat_view.clear_messages()
                    self.prompt_box.show_hints()
                    self.status_bar.clear_context_usage()
        except Exception as e:
            logger.warning(f"Could not load session history: {e}")
            self.header.show_header()
            self.chat_view.clear_messages()
            self.prompt_box.show_hints()
            self.status_bar.clear_context_usage()

    # ─── Message Actions (Revert / Copy / Fork) ───

    @on(MessageWidget.ActionRequested)
    def on_message_action_requested(self, event: MessageWidget.ActionRequested) -> None:
        """Handle click on a user message — open the Message Actions modal."""
        self._dismiss_active_modals()
        self.app.push_screen(
            MessageActionsModal(
                message_text=event.message_text,
                message_index=event.message_index,
            ),
            self._handle_message_action,
        )

    def _interrupt_active_generation(self) -> None:
        """Cancel any in-progress LLM stream and reset generation state."""
        if self._is_generating:
            if self._current_worker and not self._current_worker.is_finished:
                self._current_worker.cancel()
            self._is_generating = False
            self.status_bar.set_generating(False)

        if self.voice_controller.is_active:
            self.voice_controller.stop()
            self.prompt_box.set_listening_state(False)

    async def _count_memory_messages_before(self, user_msg_index: int) -> int:
        """Count how many memory messages exist before the Nth user message.

        The conversation store saves messages sequentially (user, assistant,
        user, assistant, ...). This finds how many total stored messages
        precede the user message at *user_msg_index* so we know where to
        truncate the buffer.
        """
        if not self.engine or not self.engine.session:
            return 0
        session_id = self.engine.session.session_id
        if (
            not self.engine.memory_manager
            or not self.engine.memory_manager.conversation
        ):
            return 0

        conv = self.engine.memory_manager.conversation
        # Ensure buffer is loaded from disk before counting
        if session_id not in conv._buffers:
            conv._buffers[session_id] = await conv._load_session(session_id)
        buf = conv._buffers.get(session_id, [])

        user_count = 0
        for i, msg in enumerate(buf):
            role = msg.get("role", "")
            # Skip system / session-title messages
            if role == "system" or msg.get("_session_title"):
                continue
            if role == "user":
                if user_count == user_msg_index:
                    return i  # truncate point: keep everything before this index
                user_count += 1
        return len(buf)

    def _cleanup_empty_session(self, session_id: str) -> None:
        """Delete a session file if it is empty (contains [] or no messages)."""
        try:
            filepath = get_sessions_dir() / f"{session_id}.json"
            if filepath.exists():
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                if not data:  # empty list
                    filepath.unlink()
                    self.snapshot_manager.clear_session(session_id)
                    logger.info(f"Cleaned up empty session file: {session_id}")
        except Exception:
            pass

    def _save_git_checkpoint(self, msg_index: int) -> None:
        """Save git working tree state and file snapshot before processing a user message.

        Captures a lightweight stash-like ref plus explicit file snapshots
        so that revert can restore the workspace to this point.
        """
        self.snapshot_manager.start_checkpoint(self._current_session_id, msg_index)
        try:
            cwd = str(Path.cwd())
            # Check if we're in a git repo
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            if res.returncode != 0:
                return

            # Get current HEAD
            head_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            head_ref = head_res.stdout.strip()

            # Create a stash-like ref (doesn't change working tree)
            stash_res = subprocess.run(
                ["git", "stash", "create"],
                capture_output=True, text=True, cwd=cwd, timeout=10,
            )
            stash_ref = stash_res.stdout.strip()

            # List untracked files
            untracked_res = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            raw = untracked_res.stdout.strip()
            untracked = set(raw.split("\n")) if raw else set()

            self._git_checkpoints[msg_index] = {
                "stash_ref": stash_ref,
                "head_ref": head_ref,
                "untracked_files": untracked,
                "cwd": cwd,
            }
        except Exception:
            pass

    def _restore_git_checkpoint(self, msg_index: int) -> bool:
        """Restore workspace to the git state captured at *msg_index*.

        Returns True if restoration succeeded.
        """
        checkpoint = self._git_checkpoints.get(msg_index)
        if not checkpoint:
            return False

        cwd = checkpoint["cwd"]
        stash_ref = checkpoint.get("stash_ref", "")
        head_ref = checkpoint.get("head_ref", "")
        old_untracked: set[str] = checkpoint.get("untracked_files", set())

        try:
            # Restore tracked files to HEAD first
            subprocess.run(
                ["git", "checkout", "HEAD", "--", "."],
                capture_output=True, text=True, cwd=cwd, timeout=15,
            )

            # Re-apply the pre-message working tree state if there was one
            if stash_ref and stash_ref != head_ref:
                subprocess.run(
                    ["git", "stash", "apply", stash_ref],
                    capture_output=True, text=True, cwd=cwd, timeout=15,
                )

            # Delete newly created untracked files (files that weren't there before)
            current_res = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            raw = current_res.stdout.strip()
            current_untracked = set(raw.split("\n")) if raw else set()

            new_files = current_untracked - old_untracked
            for f in new_files:
                fp = Path(cwd) / f
                if fp.exists() and fp.is_file():
                    fp.unlink()

            # Purge checkpoints from the reverted index onward
            keys_to_remove = [k for k in self._git_checkpoints if k >= msg_index]
            for k in keys_to_remove:
                del self._git_checkpoints[k]

            return True
        except Exception as e:
            logger.warning(f"Git checkpoint restore failed: {e}")
            return False

    async def _handle_message_action(self, result: dict[str, Any] | None) -> None:
        """Process the selected message action from MessageActionsModal."""
        if not result:
            return

        action = result["action"]
        message_text = result["message_text"]
        message_index = result["message_index"]

        if action == "copy":
            ok, msg = copy_to_clipboard(message_text)
            style_name = "success" if ok else "warning"
            self.show_toast(msg, title="Clipboard", style=style_name)

        elif action == "revert":
            await self._action_revert(message_text, message_index)

    async def _action_revert(self, message_text: str, message_index: int) -> None:
        """Revert: remove messages from index onward, truncate memory, restore files, set prompt."""
        self._interrupt_active_generation()

        # 1. Remove widgets from chat view
        self.chat_view.remove_messages_from_index(message_index)

        # 2. Truncate conversation memory
        if self.engine and self.engine.session:
            keep = await self._count_memory_messages_before(message_index)
            session_id = self.engine.session.session_id
            if (
                self.engine.memory_manager
                and self.engine.memory_manager.conversation
            ):
                await self.engine.memory_manager.conversation.truncate(
                    session_id, keep
                )

        # 3. Restore file changes via snapshot manager and git checkpoint
        snapshot_restored = self.snapshot_manager.restore_checkpoint(self._current_session_id, message_index)
        git_restored = self._restore_git_checkpoint(message_index)
        files_restored = snapshot_restored or git_restored

        # 4. Place message text into prompt box
        self.prompt_box.text = message_text
        self.prompt_box.input_field.focus()

        # 5. If chat is now empty, show header/hints and clean up empty session
        if not self.chat_view.has_messages:
            self.header.show_header()
            self.prompt_box.show_hints()
            self.status_bar.clear_context_usage()
            if self.engine and self.engine.session:
                self._cleanup_empty_session(self.engine.session.session_id)
        else:
            self._update_context_display()

        file_note = " and file changes restored" if files_restored else ""
        self.show_toast(
            f"Message reverted{file_note} — edit and resend",
            title="Reverted",
            style="info",
        )

    # ─── Modal Actions ───

    def _dismiss_active_modals(self) -> None:
        """Pop any currently active modal screen so only one modal is shown at a time."""
        from textual.screen import ModalScreen
        while len(self.app.screen_stack) > 1 and isinstance(self.app.screen, ModalScreen):
            self.app.pop_screen()

    def action_open_connect(self) -> None:
        def on_connect_done(selected_provider: dict[str, Any] | None) -> None:
            if selected_provider and isinstance(selected_provider, dict) and "id" in selected_provider:
                prov_id = selected_provider["id"]
                prov_name = selected_provider["name"]
                prov_raw = selected_provider.get("raw", {})
                env_vars = selected_provider.get("env_vars") or get_provider_env_vars(prov_id, prov_raw)
                self._prompt_provider_env_vars(prov_id, prov_name, env_vars, index=0)

        self._dismiss_active_modals()
        self.app.push_screen(ConnectModal(engine=self.engine), on_connect_done)

    def _prompt_provider_env_vars(
        self,
        prov_id: str,
        prov_name: str,
        env_vars: list[str],
        index: int = 0,
    ) -> None:
        """Sequential multi-step prompt for providers requiring N environment variables."""
        if not env_vars or index >= len(env_vars):
            self.action_open_models(only_provider=prov_id)
            return

        current_env = env_vars[index]
        label = format_env_var_label(current_env)
        is_secret = any(
            k in current_env.upper()
            for k in ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH")
        )

        title = f"Enter your {label}"
        placeholder = label

        def on_step_done(saved_provider_id: str | None) -> None:
            if saved_provider_id:
                self._prompt_provider_env_vars(prov_id, prov_name, env_vars, index=index + 1)

        self.app.push_screen(
            ApiKeyModal(
                provider_id=prov_id,
                provider_name=prov_name,
                api_key_env=current_env,
                title=title,
                placeholder=placeholder,
                password=is_secret,
                engine=self.engine,
            ),
            on_step_done,
        )

    def action_open_models(
        self,
        initial_provider: str | None = None,
        only_provider: str | None = None,
    ) -> None:
        async def on_model_selected(model_info: dict[str, str] | None) -> None:
            if model_info and self.engine and self.engine.config:
                new_model = model_info["id"]
                new_provider = model_info.get("provider", "").lower()

                if (
                    new_provider
                    and self.engine.provider_manager
                    and new_provider != self.engine.config.provider.active.lower()
                ):
                    try:
                        await self.engine.provider_manager.switch_provider(new_provider)
                        self.engine.config.provider.active = new_provider
                    except Exception as e:
                        self.chat_view.add_error_message(f"Could not switch provider to {new_provider}: {e}")

                self.engine.config.provider.model = new_model
                self.engine.config.save()
                self.update_engine_status()

        self._dismiss_active_modals()
        self.app.push_screen(
            ModelModal(
                engine=self.engine,
                initial_provider=initial_provider,
                only_provider=only_provider,
            ),
            on_model_selected,
        )

    def action_open_sessions(self) -> None:
        def on_session_selected(session_id: str | None) -> None:
            if session_id:
                if session_id == "new":
                    if self.engine:
                        from jarvis.core.session import Session
                        self.engine.session = Session(engine=self.engine)
                    self.chat_view.clear_messages()
                    self.header.show_header()
                    self.prompt_box.show_hints()
                    self.status_bar.clear_context_usage()
                else:
                    if self.engine:
                        from jarvis.core.session import Session
                        self.engine.session = Session(session_id=session_id, engine=self.engine)
                    self.load_session_history(session_id)

        self._dismiss_active_modals()
        self.app.push_screen(SessionModal(engine=self.engine), on_session_selected)

    def action_open_help(self) -> None:
        self._dismiss_active_modals()
        self.app.push_screen(HelpModal())

    def action_open_mcps(self) -> None:
        self._dismiss_active_modals()
        self.app.push_screen(MCPModal(engine=self.engine))

    def action_open_config(self) -> None:
        self._dismiss_active_modals()
        self.app.push_screen(ConfigModal(engine=self.engine))

    async def action_new_session(self) -> None:
        await self.handle_slash_command("/new")

    async def action_clear_screen(self) -> None:
        await self.handle_slash_command("/clear")

    def action_open_debug(self) -> None:
        self._dismiss_active_modals()
        self.app.push_screen(
            DebugModal(
                engine=self.engine,
                is_generating=self._is_generating,
                is_voice_active=self.voice_controller.is_active,
            )
        )

    def action_open_theme(self) -> None:
        self._dismiss_active_modals()
        self.app.push_screen(ThemeModal(engine=self.engine))

    def action_open_effort(self) -> None:
        if not self.engine or not self.engine.config or not self.engine.config.provider:
            return

        model_id = self.engine.config.provider.model
        provider_id = self.engine.config.provider.active

        from jarvis.providers.models_dev import (
            get_model_effort_values,
            has_configurable_reasoning,
            is_only_thinking_model,
        )

        efforts = get_model_effort_values(model_id, provider_id)
        if not efforts and not has_configurable_reasoning(model_id, provider_id):
            if is_only_thinking_model(model_id, provider_id):
                self.show_toast(
                    f"Model '{model_id}' is an inherent reasoning model with fixed reasoning.",
                    title="Fixed Reasoning Model",
                    style="info",
                )
            else:
                self.show_toast(
                    f"Model '{model_id}' does not support configurable reasoning effort.",
                    title="Effort Unsupported",
                    style="warning",
                )
            return

        def on_effort_selected(effort: str | None) -> None:
            if effort is not None and self.engine and self.engine.config:
                if effort.lower() == "none":
                    self.engine.config.provider.reasoning_effort = "none"
                    self.engine.config.provider.thinking = False
                else:
                    self.engine.config.provider.reasoning_effort = effort.lower()
                    self.engine.config.provider.thinking = True
                self.engine.config.save()
                self.update_engine_status()
                self.show_toast(
                    f"Reasoning effort set to: {effort}",
                    title="Effort Updated",
                    style="success",
                )

        self._dismiss_active_modals()
        self.app.push_screen(
            EffortModal(engine=self.engine, available_efforts=efforts),
            on_effort_selected,
        )

