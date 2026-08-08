from jarvis.ui.tui.commands import SlashCommand, filter_commands
from jarvis.ui.tui.widgets.command_popover import CommandPopoverWidget
from jarvis.ui.tui.widgets.prompt_box import PromptBoxWidget


def test_prompt_box_mic_button_hollow_circle():
    pb = PromptBoxWidget()
    assert str(pb.mic_button.content) == "⭕"

    pb.set_listening_state(True)
    assert str(pb.mic_button.content) == "🔴"
    assert "listening" in pb.mic_button.classes

    pb.set_listening_state(False)
    assert str(pb.mic_button.content) == "⭕"
    assert "listening" not in pb.mic_button.classes


def test_command_popover_hidden_returns_none():
    pop = CommandPopoverWidget()
    pop.current_commands = [SlashCommand("/models", "Select models")]
    pop.styles.display = "none"

    # When popover is hidden or unmounted, get_selected_command should return None
    assert pop.get_selected_command() is None


def test_slash_command_filtering():
    matches = filter_commands("/mod")
    assert any(cmd.name == "/models" for cmd in matches)

    empty_matches = filter_commands("/nonexistentcommand12345")
    assert len(empty_matches) == 0


def test_prompt_box_auto_expanding_height():
    pb = PromptBoxWidget()
    assert pb.text == ""
    pb.text = "line1\nline2\nline3"
    assert pb.text == "line1\nline2\nline3"
    assert pb.input_field.wrapped_document.height == 3


import pytest


@pytest.mark.asyncio
async def test_prompt_input_text_area_submitted_event():
    from unittest.mock import MagicMock
    from textual.events import Key
    from jarvis.ui.tui.widgets.prompt_box import PromptInputTextArea

    area = PromptInputTextArea("Hello world")
    posted_messages = []
    area.post_message = lambda message: (posted_messages.append(message), True)[1]  # type: ignore[assignment]

    event = MagicMock(spec=Key)
    event.key = "enter"
    event.shift = False
    event.alt = False
    event.ctrl = False

    await area._on_key(event)
    assert len(posted_messages) == 1
    submitted_msg = posted_messages[0]
    assert isinstance(submitted_msg, PromptInputTextArea.Submitted)
    assert submitted_msg.value == "Hello world"
    assert submitted_msg.input is area


def test_modal_dialog_search_input_has_visible_height():
    from jarvis.ui.tui.widgets.modal_dialog import ModalDialog

    dialog = ModalDialog("Test Dialog", show_search=True)
    assert dialog.search_input is not None
    assert "modal-search" in dialog.search_input.classes
    assert "height: 3;" in dialog.DEFAULT_CSS
    assert "border: solid #3b82f6;" in dialog.DEFAULT_CSS


def test_mcp_manager_available_servers_includes_registry_servers():
    from jarvis.core.config import JarvisConfig
    from jarvis.mcp.manager import MCPManager

    config = JarvisConfig()
    mgr = MCPManager(config)
    mgr.registry.load()

    available = mgr.get_available_servers()
    server_names = [s["name"] for s in available]

    assert "firecrawl-mcp" in server_names
    assert "vercel" in server_names

def test_unregister_server_removes_tools_from_platform_registry():
    from jarvis.mcp.platform.models import RegisteredTool
    from jarvis.mcp.platform.registry import platform_registry

    dummy_tool = RegisteredTool(
        name="test_tool",
        qualified_name="dummy_server__test_tool",
        server_name="dummy_server",
        description="A test tool",
        input_schema={"type": "object"},
    )
    platform_registry.register_tool(dummy_tool)
    assert platform_registry.has_tool("dummy_server__test_tool") is True

    platform_registry.unregister_server("dummy_server")
    assert platform_registry.has_tool("dummy_server__test_tool") is False


@pytest.mark.asyncio
async def test_cancelled_stream_saves_partial_message():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from jarvis.core.engine import JarvisEngine

    engine = JarvisEngine()
    engine._initialized = True
    engine.config = MagicMock()
    engine.config.provider.model = "test-model"
    engine.config.provider.temperature = 0.7
    engine.config.provider.max_tokens = 1000
    engine.config.provider.top_p = 1.0
    engine.config.tools.max_turns = 25
    engine.session = MagicMock()
    engine.session.session_id = "test_cancel_session"

    memory_mock = AsyncMock()
    memory_mock.get_context.return_value = {}
    memory_mock.conversation = AsyncMock()
    memory_mock.conversation.retrieve.return_value = []
    engine.memory_manager = memory_mock

    async def mock_stream_turn(*args, **kwargs):
        yield "Hello "
        yield "World"
        raise asyncio.CancelledError()

    engine._get_tool_definitions = AsyncMock(return_value=([], ""))
    engine._stream_turn = mock_stream_turn
    engine.provider_manager = MagicMock()

    with pytest.raises(asyncio.CancelledError):
        async for _ in engine.stream_chat("Hi"):
            pass

    memory_mock.add_message.assert_called_with("test_cancel_session", "assistant", "Hello World")


def test_tab_key_prepends_slash_and_opens_popover():
    from unittest.mock import MagicMock
    from textual.events import Key
    from jarvis.ui.tui.screens.main_screen import MainScreen

    ms = MainScreen()
    ms.prompt_box.text = ""

    event = MagicMock(spec=Key)
    event.key = "tab"

    ms.on_key(event)
    assert ms.prompt_box.text == "/"

    # When text is already typed, Tab key does not modify prompt
    ms.prompt_box.text = "Hello world"
    ms.on_key(event)
    assert ms.prompt_box.text == "Hello world"


@pytest.mark.asyncio
async def test_submit_prompt_blocked_while_generating():
    from jarvis.ui.tui.screens.main_screen import MainScreen

    ms = MainScreen()
    ms._is_generating = True
    ms.prompt_box.text = "Another query"

    await ms.submit_prompt()

    # Text remains in prompt box and chat view has no messages submitted
    assert ms.prompt_box.text == "Another query"
    assert ms.chat_view.has_messages is False


@pytest.mark.asyncio
async def test_slash_command_executes_while_generating():
    from unittest.mock import AsyncMock
    from jarvis.ui.tui.screens.main_screen import MainScreen

    ms = MainScreen()
    ms._is_generating = True
    ms.prompt_box.text = "/clear"
    ms.handle_slash_command = AsyncMock()

    await ms.submit_prompt()

    # Slash command clears prompt and executes handle_slash_command
    assert ms.prompt_box.text == ""
    ms.handle_slash_command.assert_called_with("/clear")


@pytest.mark.asyncio
async def test_copy_slash_command_silent():
    from unittest.mock import MagicMock
    from jarvis.ui.tui.screens.main_screen import MainScreen

    ms = MainScreen()
    ms.chat_view.add_user_message = MagicMock()
    msg = MagicMock()
    msg.role = "assistant"
    msg.raw_content = "Test response content"
    ms.chat_view._nodes._nodes.append(msg)

    ms.prompt_box.text = "/copy"
    await ms.submit_prompt()
    assert ms.prompt_box.text == ""
    # Should not add any UI messages for silent copy
    ms.chat_view.add_user_message.assert_not_called()


@pytest.mark.asyncio
async def test_clear_slash_command_shows_toast():
    from unittest.mock import AsyncMock, MagicMock
    from jarvis.ui.tui.screens.main_screen import MainScreen

    ms = MainScreen()
    engine = MagicMock()
    session = MagicMock()
    session.session_id = "abc123session"
    session.end = AsyncMock()
    engine.session = session
    engine.memory_manager = None
    ms.engine = engine

    ms.show_toast = MagicMock()
    await ms.handle_slash_command("/clear")

    assert ms.chat_view.has_messages is False
    ms.show_toast.assert_called_once_with(
        "Session deleted of ID abc123session",
        title="Session Reset",
        style="info",
    )


def test_notification_toast_widget():
    from jarvis.ui.tui.widgets.toast import NotificationToast

    toast = NotificationToast()
    assert toast.label is not None
    assert "layer: overlay;" in toast.DEFAULT_CSS


@pytest.mark.asyncio
async def test_chat_view_tool_call_resets_current_assistant_widget():
    from textual.app import App
    from jarvis.ui.tui.widgets.chat_view import ChatViewWidget, MessageWidget, ToolCallWidget

    class TestApp(App):
        def compose(self):
            yield ChatViewWidget(id="chat")

    app = TestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        chat.start_assistant_stream()
        assert chat._current_assistant_widget is not None

        # Simulate text chunk before tool call
        chat.append_assistant_chunk("Let me check Telegram...")
        first_widget = chat._current_assistant_widget
        assert first_widget is not None
        assert first_widget.raw_content == "Let me check Telegram..."

        # Add tool call
        chat.add_tool_call("Telegram_List_Dialogs", "")
        assert chat._current_assistant_widget is None

        # Append response text chunk after tool call
        chat.append_assistant_chunk("Found 10 messages: tokenrouter.com")
        second_widget = chat._current_assistant_widget
        assert second_widget is not None
        assert second_widget is not first_widget
        assert second_widget.raw_content == "Found 10 messages: tokenrouter.com"

        # Verify children order: first text widget, then tool call widget, then second text widget
        children = list(chat.children)
        assert len(children) == 3
        assert isinstance(children[0], MessageWidget)
        assert children[0].raw_content == "Let me check Telegram..."
        assert isinstance(children[1], ToolCallWidget)
        assert isinstance(children[2], MessageWidget)
        assert children[2].raw_content == "Found 10 messages: tokenrouter.com"


@pytest.mark.asyncio
async def test_pasted_text_badge_in_prompt_box():
    from unittest.mock import MagicMock
    from textual.widgets import TextArea
    from jarvis.ui.tui.app import JarvisTUIApp
    from jarvis.ui.tui.screens.main_screen import MainScreen

    app = JarvisTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)
        box = screen.prompt_box
        long_code = "print('hello world')\n" * 10  # 10 lines, > 200 chars

        # 1. Test direct text assignment
        box.text = long_code
        assert box._pasted_text == long_code
        assert "visible" in box.paste_badge.classes

        # User types additional context prompt next to badge
        box.input_field.load_text("explain this code")
        assert box.text == f"{long_code}\n\nexplain this code"

        # Clearing resets pasted attachment
        box.clear()
        assert box._pasted_text == ""
        assert box._prefix_text == ""

        # 2. Test typing "see this " then pasting long code
        box.input_field.load_text("see this ")
        box._last_known_text = "see this "

        # Simulate paste event in input_field
        box.input_field.load_text("see this " + long_code)
        box.on_text_changed(MagicMock(spec=TextArea.Changed))

        assert box._prefix_text == "see this "
        assert box._pasted_text == long_code
        assert "visible" in box.prefix_label.classes
        assert "visible" in box.paste_badge.classes
        assert box.input_field.text == ""

        # Suffix text typed after badge
        box.input_field.load_text("fix this bug")
        assert box.text == f"see this \n\n{long_code}\n\nfix this bug"

        # Backspacing when input_field is empty clears pasted attachment and restores prefix text
        box.input_field.load_text("")
        box.clear_pasted_text()
        assert box._pasted_text == ""
        assert box.input_field.text == "see this "


@pytest.mark.asyncio
async def test_prompt_history_up_down_navigation():
    from unittest.mock import MagicMock
    from textual.events import Key
    from jarvis.ui.tui.app import JarvisTUIApp
    from jarvis.ui.tui.screens.main_screen import MainScreen

    app = JarvisTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)
        screen.process_user_query = MagicMock()

        # Submit 2 prompts to populate history
        screen.prompt_box.text = "first prompt"
        await screen.submit_prompt()

        screen.prompt_box.text = "second prompt"
        await screen.submit_prompt()

        # Press PageUp to navigate back in history
        pageup_event = MagicMock(spec=Key)
        pageup_event.key = "pageup"
        screen.on_key(pageup_event)
        assert screen.prompt_box.text == "second prompt"

        screen.on_key(pageup_event)
        assert screen.prompt_box.text == "first prompt"

        # Press PageDown to navigate forward in history
        pagedown_event = MagicMock(spec=Key)
        pagedown_event.key = "pagedown"
        screen.on_key(pagedown_event)
        assert screen.prompt_box.text == "second prompt"

        screen.on_key(pagedown_event)
        assert screen.prompt_box.text == ""


@pytest.mark.asyncio
async def test_voice_mode_auto_interrupt_on_submit():
    from unittest.mock import MagicMock
    from jarvis.ui.tui.app import JarvisTUIApp
    from jarvis.ui.tui.screens.main_screen import MainScreen

    app = JarvisTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)
        screen.process_user_query = MagicMock()
        screen.voice_controller.is_active = True

        screen.prompt_box.text = "Typed prompt while in voice mode"
        await screen.submit_prompt()

        # Voice controller should be stopped and prompt processed
        assert screen.voice_controller.is_active is False
        screen.process_user_query.assert_called_once_with("Typed prompt while in voice mode")


@pytest.mark.asyncio
async def test_voice_mode_auto_send_msg_false_populates_prompt_box():
    from unittest.mock import AsyncMock, MagicMock
    from jarvis.ui.tui.app import JarvisTUIApp
    from jarvis.ui.tui.screens.main_screen import MainScreen

    app = JarvisTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)

        # Mock engine voice config auto_send_msg = False
        mock_engine = MagicMock()
        mock_engine.config.voice.auto_send_msg = False
        mock_vm = AsyncMock()
        mock_vm.stop = MagicMock()
        mock_vm.listen.return_value = "transcribed spoken query"
        mock_engine.voice_manager = mock_vm
        screen.engine = mock_engine
        screen.voice_controller.engine = mock_engine

        # Pre-populate prompt box with existing text and cursor at end
        screen.prompt_box.input_field.load_text("Hello ")
        screen.prompt_box.input_field.move_cursor((0, 6))
        screen.prompt_box._last_known_text = "Hello "

        # Run voice loop worker
        screen.voice_controller.is_active = True
        worker = screen.run_voice_loop()
        await worker.wait()

        # Should insert transcribed text at cursor position without overwriting existing text or sending
        assert screen.prompt_box.text == "Hello transcribed spoken query"
        assert screen.voice_controller.is_active is False











