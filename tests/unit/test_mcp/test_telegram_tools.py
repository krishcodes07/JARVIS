"""
Unit tests for Telegram MCP Server tools.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.mcp.platform.loader import ServerPackageLoader
from jarvis.mcp.servers.telegram.tools.create_group import create_group
from jarvis.mcp.servers.telegram.tools.download_media import download_media
from jarvis.mcp.servers.telegram.tools.forward_messages import forward_messages
from jarvis.mcp.servers.telegram.tools.get_chat_members import get_chat_members
from jarvis.mcp.servers.telegram.tools.mark_read import mark_read
from jarvis.mcp.servers.telegram.tools.pin_message import pin_message
from jarvis.mcp.servers.telegram.tools.react_to_msg import react_to_msg
from jarvis.mcp.servers.telegram.tools.send_file import send_file
from jarvis.mcp.servers.telegram.tools.send_voice_note import send_voice_note


def test_telegram_tools_discovery():
    """Verify that ServerPackageLoader discovers all 20 Telegram tools."""
    server_dir = Path(__file__).resolve().parents[3] / "src" / "jarvis" / "mcp" / "servers" / "telegram"
    loader = ServerPackageLoader(server_dir)
    discovered = loader.discover_tools()

    tool_names = {t.name for t in discovered}

    expected_tools = {
        "delete_message",
        "edit_message",
        "get_account_info",
        "get_bot_info",
        "get_contacts",
        "list_dialogs",
        "read_messages",
        "reply_message",
        "search_messages",
        "send_message",
        "send_photo",
        # New tools
        "send_file",
        "react_to_msg",
        "pin_message",
        "forward_messages",
        "download_media",
        "get_chat_members",
        "mark_read",
        "send_voice_note",
        "create_group",
    }

    assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"


@patch("jarvis.mcp.servers.telegram.tools.send_file.get_telegram_client")
def test_send_file_unauthorized(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = False
    mock_get_client.return_value = mock_client

    result = send_file("123456", "test.pdf")
    assert "Error: Telegram user session is not authorized" in result


@patch("jarvis.mcp.servers.telegram.tools.send_file.get_telegram_client")
def test_send_file_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_sent_msg = MagicMock()
    mock_sent_msg.id = 999
    mock_client.send_file.return_value = mock_sent_msg
    mock_get_client.return_value = mock_client

    result = send_file("@testuser", "test.pdf", caption="Here is the report")
    assert "[OK]" in result
    assert "Message ID: 999" in result
    mock_client.send_file.assert_called_once_with(
        "@testuser", "test.pdf", caption="Here is the report", reply_to=None, force_document=False
    )


@patch("jarvis.mcp.servers.telegram.tools.react_to_msg.get_telegram_client")
def test_react_to_msg_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_client.get_input_entity.return_value = "input_entity_123"
    mock_get_client.return_value = mock_client

    result = react_to_msg("12345", 50, reaction="🔥")
    assert "[OK] Reacted '🔥' to message ID 50" in result


@patch("jarvis.mcp.servers.telegram.tools.pin_message.get_telegram_client")
def test_pin_message_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_get_client.return_value = mock_client

    result = pin_message("12345", 50, unpin=False, notify=True)
    assert "[OK] Pinned message ID 50" in result
    mock_client.pin_message.assert_called_once_with(12345, 50, notify=True)


@patch("jarvis.mcp.servers.telegram.tools.forward_messages.get_telegram_client")
def test_forward_messages_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_client.forward_messages.return_value = [MagicMock(), MagicMock()]
    mock_get_client.return_value = mock_client

    result = forward_messages("1111", "2222", "10,11")
    assert "[OK] Successfully forwarded 2 message(s)" in result
    mock_client.forward_messages.assert_called_once_with(2222, [10, 11], 1111)


@patch("jarvis.mcp.servers.telegram.tools.download_media.get_telegram_client")
def test_download_media_no_media(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_msg = MagicMock()
    mock_msg.media = None
    mock_client.get_messages.return_value = mock_msg
    mock_get_client.return_value = mock_client

    result = download_media("12345", 42)
    assert "does not contain downloadable media" in result


@patch("jarvis.mcp.servers.telegram.tools.download_media.os.path.getsize", return_value=100)
@patch("jarvis.mcp.servers.telegram.tools.download_media.os.path.exists", return_value=True)
@patch("jarvis.mcp.servers.telegram.tools.download_media.get_telegram_client")
def test_download_media_totallist_handling(mock_get_client, mock_exists, mock_getsize):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True

    mock_msg = MagicMock()
    mock_msg.media = MagicMock()
    # Simulate get_messages returning a list/TotalList
    mock_client.get_messages.return_value = [mock_msg]
    mock_client.download_media.return_value = "downloads/telegram/photo.jpg"
    mock_get_client.return_value = mock_client

    result = download_media("12345", 42)
    assert "[OK] Downloaded media" in result


@patch("jarvis.mcp.servers.telegram.tools.get_chat_members.get_telegram_client")
def test_get_chat_members_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    
    user1 = MagicMock()
    user1.id = 1001
    user1.first_name = "Alice"
    user1.last_name = "Smith"
    user1.username = "alice_s"
    user1.bot = False

    user2 = MagicMock()
    user2.id = 1002
    user2.first_name = "Botty"
    user2.last_name = None
    user2.username = "botty_bot"
    user2.bot = True

    mock_client.get_participants.return_value = [user1, user2]
    mock_get_client.return_value = mock_client

    result = get_chat_members("@testgroup", limit=10)
    assert "Found 2 member(s)" in result
    assert "Alice Smith (@alice_s)" in result
    assert "Botty (@botty_bot) [BOT]" in result


@patch("jarvis.mcp.servers.telegram.tools.mark_read.get_telegram_client")
def test_mark_read_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_get_client.return_value = mock_client

    result = mark_read("12345", max_id=150)
    assert "[OK] Marked messages as read in chat '12345' up to message ID 150." in result
    mock_client.send_read_acknowledge.assert_called_once_with(12345, max_id=150)


@patch("jarvis.mcp.servers.telegram.tools.send_voice_note.get_telegram_client")
def test_send_voice_note_success(mock_get_client):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_sent_msg = MagicMock()
    mock_sent_msg.id = 888
    mock_client.send_file.return_value = mock_sent_msg
    mock_get_client.return_value = mock_client

    result = send_voice_note("@testuser", "audio.ogg")
    assert "[OK] Voice note 'audio.ogg' sent" in result
    mock_client.send_file.assert_called_once_with(
        "@testuser", "audio.ogg", voice_note=True, caption=None, reply_to=None
    )


@patch("jarvis.mcp.servers.telegram.tools.create_group.utils.get_input_user")
@patch("jarvis.mcp.servers.telegram.tools.create_group.get_telegram_client")
def test_create_group_success(mock_get_client, mock_get_input_user):
    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True
    mock_client.get_input_entity.side_effect = lambda x: f"entity_{x}"
    mock_get_input_user.side_effect = lambda x: f"input_user_{x}"

    mock_res = MagicMock()
    mock_chat = MagicMock()
    mock_chat.id = 777
    mock_res.chats = [mock_chat]
    mock_client.return_value = mock_res
    mock_get_client.return_value = mock_client

    result = create_group("Project Team", "@john,@alice")
    assert "[OK] Successfully created group chat 'Project Team'" in result
    assert "(Chat ID: 777)" in result
