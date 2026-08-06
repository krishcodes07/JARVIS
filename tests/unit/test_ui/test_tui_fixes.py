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
    from jarvis.ui.tui.widgets.prompt_box import PromptInputTextArea

    area = PromptInputTextArea("Hello world")
    posted_messages = []
    area.post_message = lambda msg: posted_messages.append(msg)

    class MockEvent:
        key = "enter"
        shift = False
        alt = False
        ctrl = False

        def prevent_default(self):
            pass

        def stop(self):
            pass

    await area._on_key(MockEvent())
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





