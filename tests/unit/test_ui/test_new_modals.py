"""
Unit tests for new TUI modals and VoiceSessionController.
"""

from __future__ import annotations

from jarvis.ui.tui.screens.modals import ConfigModal, ConfirmModal, DebugModal
from jarvis.ui.tui.voice_controller import VoiceSessionController


def test_confirm_modal_init():
    modal = ConfirmModal(message="Delete test session?", title="Confirm Delete")
    assert modal.message_text == "Delete test session?"
    assert modal.dialog is not None


def test_config_modal_init():
    modal = ConfigModal(engine=None)
    assert modal.engine is None
    assert modal.dialog is not None


def test_debug_modal_init():
    modal = DebugModal(engine=None, is_generating=False, is_voice_active=False)
    assert modal.is_generating is False
    assert modal.is_voice_active is False
    assert modal.dialog is not None


def test_voice_controller_status_when_disconnected():
    controller = VoiceSessionController(engine=None)
    assert controller.is_active is False
    info = controller.get_status_info()
    assert info["active"] is False
    assert info["initialized"] is False


def test_app_import():
    from jarvis.ui.tui.app import JarvisTUIApp
    app = JarvisTUIApp(engine=None)
    assert app.TITLE == "JARVIS AI Assistant"


def test_slash_command_new_registration():
    from jarvis.ui.tui.commands import COMMAND_REGISTRY, filter_commands, get_command
    cmd = get_command("/new")
    assert cmd is not None
    assert cmd.name == "/new"
    assert "Start a new conversation session" in cmd.description
    filtered = filter_commands("/new")
    assert len(filtered) == 1
    assert filtered[0].name == "/new"


def test_main_screen_action_open_connect_signature():
    from jarvis.ui.tui.screens.main_screen import MainScreen
    screen = MainScreen(engine=None)
    assert hasattr(screen, "action_open_connect")
    assert hasattr(screen, "action_open_models")


