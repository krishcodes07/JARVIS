"""
Main Screen — Primary workspace view for JARVIS Terminal UI.
OpenCode/ClaudeCode layout: header hides on first message, compact prompt at bottom.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, ClassVar

from textual import events, on, work
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual.widgets import Button, Input, TextArea
from textual.worker import get_current_worker

from jarvis.core.config import DATA_DIR
from jarvis.ui.tui.screens.modals import (
    ConfigModal,
    DebugModal,
    HelpModal,
    MCPModal,
    ModelModal,
    SessionModal,
)
from jarvis.ui.tui.voice_controller import VoiceSessionController
from jarvis.ui.tui.widgets import (
    ChatViewWidget,
    CommandPopoverWidget,
    HeaderWidget,
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
        Binding("ctrl+m", "open_models", "Models", show=False),
        Binding("ctrl+s", "open_sessions", "Sessions", show=False),
        Binding("ctrl+h", "open_help", "Help", show=False),
        Binding("alt+v", "toggle_voice", "Voice Mode", show=False),
    ]

    def __init__(self, engine: JarvisEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.voice_controller = VoiceSessionController(engine=self.engine)
        self.header = HeaderWidget(id="header-container")
        self.chat_view = ChatViewWidget(id="chat-scroll")
        self.popover = CommandPopoverWidget(id="command-popover")
        self.prompt_box = PromptBoxWidget(id="prompt-card")
        self.status_bar = StatusBarWidget(id="status-bar")
        self._is_generating: bool = False
        self._current_worker = None


    def compose(self):
        yield self.header
        yield self.chat_view
        yield self.popover
        yield self.prompt_box
        yield self.status_bar

    def on_mount(self) -> None:
        self.prompt_box.input_field.focus()
        self.update_engine_status()
        # Load current session history
        if self.engine and self.engine.session:
            self.load_session_history(self.engine.session.session_id)

        if not self.chat_view.has_messages:
            self.header.show_header()
            self.chat_view.clear_messages()
            self.prompt_box.show_hints()

    def on_first_message(self) -> None:
        """Called by ChatViewWidget when the first message appears. Hide header and hints."""
        self.header.hide_header()
        self.prompt_box.hide_hints()

    def update_engine_status(self) -> None:
        if self.engine and self.engine.config:
            c = self.engine.config
            self.prompt_box.update_badges(
                mode="",
                model=c.provider.model,
                provider=c.provider.active,
                reasoning="high",
            )

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

        if self.prompt_box.input_field.has_focus:
            if event.key == "tab":
                if is_slash:
                    selected_cmd = self.popover.get_selected_command()
                    if selected_cmd:
                        # Autocomplete text into input box so user can add arguments
                        self.prompt_box.text = selected_cmd.name + " "
                        self.popover.hide()
                        event.prevent_default()
                        event.stop()
                        return
                else:
                    # Do not destroy user prompt when Tab is pressed on normal text
                    event.prevent_default()
                    event.stop()
                    return
            elif is_slash and event.key == "down":
                self.popover.highlight_next()
                event.prevent_default()
                event.stop()
            elif is_slash and event.key == "up":
                self.popover.highlight_prev()
                event.prevent_default()
                event.stop()

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

        self.prompt_box.clear()
        self.popover.hide()

        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

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

        self._current_worker = get_current_worker()
        self._is_generating = True
        self.status_bar.set_generating(True)

        self.chat_view.start_assistant_stream()

        async def on_tool_call(tool_name: str, tool_args: dict):
            args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
            self.chat_view.add_tool_call(tool_name, args_str)

        def on_tool_result(tool_name: str, result: str):
            res_str = result[:150] + "..." if len(result) > 150 else result
            self.chat_view.add_tool_output(res_str)

        async def approval_callback(tool_name: str, tool_args: dict) -> bool:
            args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
            self.chat_view.add_tool_call(f"APPROVAL REQUIRED: {tool_name}", args_str)
            return True

        model_name = self.engine.config.provider.model if self.engine.config else "JARVIS"

        try:
            async for chunk in self.engine.stream_chat(
                query,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
                approval_callback=approval_callback,
            ):
                self.chat_view.append_assistant_chunk(chunk)

            self.chat_view.finish_assistant_stream(mode="", model_name=model_name)

        except asyncio.CancelledError:
            logger.info("Chat stream cancelled by user.")
            self.chat_view.add_error_message("Generation stopped by user.")
        except Exception as e:
            logger.exception("Error during chat processing")
            self.chat_view.finish_assistant_stream(mode="", model_name=model_name)
            self.chat_view.add_error_message(f"Error: {e}")
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

                # 2. Reset listening UI state while processing response
                self.prompt_box.set_listening_state(False)
                user_query = spoken_text.strip()
                self.prompt_box.clear()
                self.chat_view.add_user_message(user_query)

                # 3. Stream LLM response
                model_name = self.engine.config.provider.model if (self.engine and self.engine.config) else "JARVIS"
                self.chat_view.start_assistant_stream()
                accumulated_response: list[str] = []

                async def on_tool_call(tool_name: str, tool_args: dict):
                    args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
                    self.chat_view.add_tool_call(tool_name, args_str)

                def on_tool_result(tool_name: str, result: str):
                    res_str = result[:150] + "..." if len(result) > 150 else result
                    self.chat_view.add_tool_output(res_str)

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
            "/exit": self.app.exit,
            "/quit": self.app.exit,
            "/sessions": self.action_open_sessions,
            "/models": self.action_open_models,
            "/help": self.action_open_help,
            "/mcp": self.action_open_mcps,
            "/config": self.action_open_config,
            "/debug": self.action_open_debug,
            "/voice": self.action_toggle_voice,
        }

        if cmd in modal_handlers:
            modal_handlers[cmd]()
            if cmd == "/voice":
                status = "enabled (listening)" if self.voice_controller.is_active else "disabled"
                self.chat_view.add_user_message(f"✓ Hands-free voice mode toggled: {status}")
            return

        if cmd == "/clear":
            if self.engine:
                from jarvis.core.session import Session
                self.engine.session = Session(engine=self.engine)
            self.chat_view.clear_messages()
            self.header.show_header()
            self.prompt_box.show_hints()

        elif cmd == "/provider":
            if args and self.engine and self.engine.provider_manager:
                provider_name = args[0].lower()
                try:
                    await self.engine.provider_manager.switch_provider(provider_name)
                    if self.engine.config:
                        self.engine.config.provider.active = provider_name
                        self.engine.config.save()
                    self.update_engine_status()
                    self.chat_view.add_user_message(f"✓ Switched provider to: {provider_name}")
                except Exception as e:
                    self.chat_view.add_error_message(f"Failed to switch provider: {e}")
            else:
                self.action_open_models()

        elif cmd in ("/model", "/connect") and args:
            model_name = args[0]
            if self.engine and self.engine.config:
                self.engine.config.provider.model = model_name
                self.engine.config.save()
                self.update_engine_status()
                self.chat_view.add_user_message(f"✓ Switched active model to: {model_name}")

        elif cmd in ("/stt", "/tts", "/voices"):
            info = self.voice_controller.get_status_info()
            self.chat_view.add_user_message(
                f"**Voice Subsystem Info**\n"
                f"- **STT Provider**: {info['stt_provider']}\n"
                f"- **TTS Provider**: {info['tts_provider']}\n"
                f"- **Status**: {'Ready' if info['initialized'] else 'Disabled'}"
            )

        else:
            self.chat_view.add_error_message(f"Unknown command '{cmd}'. Type /help for available commands.")

    def load_session_history(self, session_id: str) -> None:
        filepath = DATA_DIR / "conversations" / f"{session_id}.json"
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
                    else:
                        self.header.show_header()
                        self.chat_view.clear_messages()
                        self.prompt_box.show_hints()
                else:
                    self.header.show_header()
                    self.chat_view.clear_messages()
                    self.prompt_box.show_hints()
        except Exception as e:
            logger.warning(f"Could not load session history: {e}")
            self.header.show_header()
            self.chat_view.clear_messages()
            self.prompt_box.show_hints()

    # ─── Modal Actions ───

    def action_open_models(self) -> None:
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

        self.app.push_screen(ModelModal(engine=self.engine), on_model_selected)

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
                else:
                    if self.engine:
                        from jarvis.core.session import Session
                        self.engine.session = Session(session_id=session_id, engine=self.engine)
                    self.load_session_history(session_id)

        self.app.push_screen(SessionModal(engine=self.engine), on_session_selected)

    def action_open_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_open_mcps(self) -> None:
        self.app.push_screen(MCPModal(engine=self.engine))

    def action_open_config(self) -> None:
        self.app.push_screen(ConfigModal(engine=self.engine))

    def action_open_debug(self) -> None:
        self.app.push_screen(
            DebugModal(
                engine=self.engine,
                is_generating=self._is_generating,
                is_voice_active=self.voice_controller.is_active,
            )
        )

