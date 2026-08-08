"""Headless smoke tests for the reusable JARVIS UI."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from jarvis_gui.config import UIConfig
from jarvis_gui.conversation_store import ConversationStore
from jarvis_gui.dummy_ai import DummyAIService
from jarvis_gui.main_window import JarvisWindow
from jarvis_gui.themes import get_theme


def get_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_dummy_service_returns_contextual_response() -> None:
    response = DummyAIService._build_response("Can you help with Python code?")
    assert "dummy response" in response.lower()


def test_theme_can_override_accent() -> None:
    theme = get_theme("Obsidian", "Solar Amber")
    assert theme.name == "Obsidian"
    assert theme.accent == "#d7a455"


def test_config_load_uses_concrete_dataclass_defaults(tmp_path) -> None:
    settings = QSettings(
        str(tmp_path / "settings.ini"), QSettings.Format.IniFormat
    )

    config = UIConfig.load(settings)

    assert config == UIConfig()


def test_conversation_store_persists_messages(tmp_path) -> None:
    database_path = tmp_path / "history.db"
    store = ConversationStore(database_path)
    conversation_id = store.create_conversation("Persistent chat")
    store.add_message(conversation_id, "user", "Remember this")
    store.add_message(conversation_id, "assistant", "Saved locally")

    reopened_store = ConversationStore(database_path)
    conversations = reopened_store.list_conversations()
    messages = reopened_store.get_messages(conversation_id)

    assert conversations[0].title == "Persistent chat"
    assert conversations[0].message_count == 2
    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == [
        "Remember this",
        "Saved locally",
    ]


def test_window_builds_and_renders_offscreen(tmp_path) -> None:
    app = get_app()
    config = UIConfig(animation_speed=0, particle_density=10)
    window = JarvisWindow(
        config=config,
        ai_service=DummyAIService(delay_ms=0),
        conversation_store=ConversationStore(tmp_path / "window.db"),
    )
    window.resize(1000, 650)
    window.show()
    app.processEvents()

    assert window.orb.isVisible()
    assert window.prompt_bar.input.placeholderText() == "Ask me anything..."
    assert not window.conversation_view.isVisible()
    assert window.settings_button.graphicsEffect() is None

    window.settings_button.click()
    assert window.page_stack.currentWidget() is window.settings
    window.settings.back_button.click()
    assert window.page_stack.currentWidget() is window.assistant_page
    assert not window.grab().isNull()
    window.close()


def test_prompt_submission_saves_and_reopens_conversation(tmp_path) -> None:
    app = get_app()
    store = ConversationStore(tmp_path / "messages.db")
    window = JarvisWindow(
        config=UIConfig(animation_speed=0),
        ai_service=DummyAIService(delay_ms=0),
        conversation_store=store,
    )
    window.show()
    window.submit_prompt("Hello JARVIS")
    app.processEvents()
    app.processEvents()

    conversation_id = window.current_conversation_id
    assert conversation_id is not None
    assert window.conversation_view.isVisible()
    assert window.conversation_view.message_count == 2
    assert [message.role for message in store.get_messages(conversation_id)] == [
        "user",
        "assistant",
    ]
    assert store.list_conversations()[0].title == "Hello JARVIS"
    assert window.prompt_bar.input.isEnabled()
    assert window.orb.is_speaking
    assert window.orb.status == "SPEAKING"
    for _ in range(5):
        window.orb._advance()
    assert any(abs(level) > 0.01 for level in window.orb._voice_bands)

    window._finish_speaking()
    assert not window.orb.is_speaking
    assert window.orb.status == "ONLINE • READY"

    window.start_new_chat()
    assert not window.conversation_view.isVisible()
    window.open_conversation(conversation_id)
    assert window.conversation_view.message_count == 2
    assert window.current_conversation_id == conversation_id
    window.close()
