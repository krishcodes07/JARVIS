"""Unit tests for GUI ConversationStore."""

import pytest

from jarvis.ui.gui.store import ConversationStore


def test_conversation_store_crud(tmp_path):
    db_path = tmp_path / "test_conversations.db"
    store = ConversationStore(db_path)

    # Create conversation
    conv_id = store.create_conversation("Test Conversation")
    assert isinstance(conv_id, str)
    assert len(conv_id) > 0

    # Add message
    msg_id = store.add_message(conv_id, "user", "Hello JARVIS")
    assert isinstance(msg_id, int)
    assert msg_id > 0

    # Add response
    msg_id2 = store.add_message(conv_id, "assistant", "Hello! How can I help?")
    assert isinstance(msg_id2, int)
    assert msg_id2 > msg_id

    # List conversations
    conversations = store.list_conversations()
    assert len(conversations) == 1
    assert conversations[0].id == conv_id
    assert conversations[0].title == "Test Conversation"
    assert conversations[0].message_count == 2

    # Get messages
    messages = store.get_messages(conv_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello JARVIS"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hello! How can I help?"


def test_add_message_validation(tmp_path):
    db_path = tmp_path / "test_conversations.db"
    store = ConversationStore(db_path)
    conv_id = store.create_conversation("Validation Test")

    with pytest.raises(ValueError, match="Unsupported conversation role"):
        store.add_message(conv_id, "system", "invalid role")

    with pytest.raises(ValueError, match="cannot be empty"):
        store.add_message(conv_id, "user", "   ")


def test_conversation_view_clear_and_pending():
    from PySide6.QtWidgets import QApplication

    from jarvis.ui.gui.themes import get_theme
    from jarvis.ui.gui.widgets.chat_view import ConversationView

    app = QApplication.instance() or QApplication([])
    view = ConversationView(get_theme("Midnight", "Electric Blue"))

    # Add messages
    view.add_message("user", "Hello")
    view.add_message("assistant", "<think:6124c78e>Analyzing query</think:6124c78e>Hello world!")

    # Show pending
    view.show_pending()
    assert view.pending_widget is not None

    # Hide pending
    view.hide_pending()
    assert view.pending_widget is None

    # Clear messages multiple times (ensure no NoneType errors)
    view.clear_messages()
    view.clear_messages()

    # Add messages again and clear with pending active
    view.add_message("user", "What's the status?")
    view.show_pending()
    view.clear_messages()
    assert view.pending_widget is None

