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









