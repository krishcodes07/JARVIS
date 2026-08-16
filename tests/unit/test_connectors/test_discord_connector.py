"""
Unit tests for JARVIS Discord Connector and Formatter.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.connectors.discord.connector import DiscordConnector
from jarvis.connectors.discord.formatter import (
    markdown_to_discord_markdown,
    split_discord_message,
)
from jarvis.core.config import JarvisConfig


def test_markdown_to_discord_markdown_formatter():
    """Test converting standard markdown to Discord-safe markdown."""
    raw_md = """# Title
Here is **bold** and *italic*.
Code: `x = 10`

```python
def hello():
    return "world"
```
"""
    formatted = markdown_to_discord_markdown(raw_md)
    assert "# Title" in formatted
    assert "**bold**" in formatted
    assert "*italic*" in formatted
    assert "`x = 10`" in formatted
    assert "```python\ndef hello():\n    return \"world\"\n```" in formatted


def test_markdown_to_discord_markdown_with_think_tags():
    """Test converting <think> tags to Discord spoiler blockquotes."""
    raw = "<think>Analyzing database schema\nStep 1: check tables</think>Here is the table list."
    formatted = markdown_to_discord_markdown(raw)

    assert "> 💭 **Thought**" in formatted
    assert "||" in formatted
    assert "Analyzing database schema" in formatted
    assert "Here is the table list." in formatted


def test_markdown_to_discord_markdown_tables():
    """Test converting Markdown tables to Discord monospace code blocks."""
    table_md = """Summary Table:

| Item | Value |
|---|---|
| Speed | 100 mph |
| Distance | 50 miles |

Done."""
    formatted = markdown_to_discord_markdown(table_md)

    assert "Summary Table:" in formatted
    assert "```text" in formatted
    assert "Item" in formatted
    assert "Value" in formatted
    assert "│" in formatted
    assert "─┼─" in formatted
    assert "Done." in formatted


def test_split_discord_message():
    """Test splitting long text to stay within Discord 2000 character limit."""
    short_text = "Short message"
    assert split_discord_message(short_text) == ["Short message"]

    long_text = ("A" * 1500 + "\n\n" + "B" * 1500)
    chunks = split_discord_message(long_text, max_length=2000)
    assert len(chunks) == 2
    assert len(chunks[0]) <= 2000
    assert len(chunks[1]) <= 2000


def test_discord_connector_config_and_filtering():
    """Test DiscordConnector config properties and channel/guild allowlists."""
    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.discord.enabled = True
    config.connectors.discord.bot_token = "mock_discord_token"
    config.connectors.discord.allowed_channels = ["123", "456"]
    config.connectors.discord.allowed_guilds = ["999"]
    config.connectors.discord.allowed_users = ["user1"]

    engine = MagicMock()
    connector = DiscordConnector(config, engine)

    assert connector.is_enabled is True
    assert connector.is_channel_allowed("123") is True
    assert connector.is_channel_allowed("789") is False

    assert connector.is_guild_allowed("999") is True
    assert connector.is_guild_allowed("888") is False
    assert connector.is_guild_allowed(None) is True  # DMs have None guild_id

    assert connector.is_user_allowed("user1") is True
    assert connector.is_user_allowed("user2") is False


@pytest.mark.asyncio
async def test_discord_connector_lifecycle():
    """Test DiscordConnector start and stop."""
    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.discord.enabled = True
    config.connectors.discord.bot_token = "mock_discord_token"

    engine = MagicMock()
    connector = DiscordConnector(config, engine)

    with patch("discord.Client") as mock_client_cls:
        events = {}
        mock_client = MagicMock()
        def fake_event(func):
            events[func.__name__] = func
            return func
        mock_client.event = fake_event
        async def fake_start(token):
            if "on_ready" in events:
                await events["on_ready"]()
        mock_client.start = AsyncMock(side_effect=fake_start)
        mock_client.close = AsyncMock()
        mock_client.is_closed.return_value = False
        mock_client.user = MagicMock()
        mock_client.user.id = 12345
        mock_client.change_presence = AsyncMock()
        mock_client_cls.return_value = mock_client

        # Start connector
        await connector.start()
        assert connector._client is not None
        assert connector.is_running is True

        # Stop connector
        await connector.stop()
        assert not connector.is_running
        mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_discord_connector_message_handling_with_thinking():
    """Test message handling with live thinking indicator and response delivery."""
    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.discord.enabled = True
    config.connectors.discord.bot_token = "mock_discord_token"

    engine = MagicMock()

    async def mock_stream(text, session_id=None, on_tool_call=None, on_tool_result=None):
        if on_tool_call:
            await on_tool_call("web_search", {"q": "AI"})
        if on_tool_result:
            await on_tool_result("web_search", "Results found")
        yield "<think>Analyzing AI news</think>"
        yield "Here is the top AI news."

    engine.stream_chat = mock_stream

    connector = DiscordConnector(config, engine)
    connector._running = True

    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1111
    mock_user.bot = False
    mock_client.user = mock_user
    connector._client = mock_client

    # Mock Discord incoming message
    mock_msg = MagicMock()
    mock_msg.author = MagicMock()
    mock_msg.author.id = 2222
    mock_msg.author.name = "krish"
    mock_msg.author.display_name = "Krish"
    mock_msg.author.bot = False
    mock_msg.content = "What is new in AI?"
    mock_msg.attachments = []
    mock_msg.guild = None  # Direct Message
    mock_msg.channel = MagicMock()
    mock_msg.channel.id = 3333
    mock_msg.channel.typing = MagicMock()

    # Async context manager for typing
    class MockTypingContext:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_msg.channel.typing.return_value = MockTypingContext()

    mock_placeholder = MagicMock()
    mock_placeholder.edit = AsyncMock()
    mock_msg.reply = AsyncMock(return_value=mock_placeholder)

    await connector._handle_message(mock_msg)

    # Initial placeholder reply was sent
    mock_msg.reply.assert_awaited()

    # Placeholder was edited with status updates and final answer
    assert mock_placeholder.edit.await_count >= 2

    # Check that tool call or thinking status was passed to edit
    edit_contents = [call.kwargs.get("content") for call in mock_placeholder.edit.await_args_list]
    assert any("Calling `web_search`" in (c or "") for c in edit_contents)

    # Final edit has the formatted answer with thought spoiler
    final_content = edit_contents[-1]
    assert final_content is not None
    assert "Thought" in final_content
    assert "Here is the top AI news." in final_content


@pytest.mark.asyncio
async def test_discord_connector_send_message_and_file(tmp_path):
    """Test send_message and send_file methods on DiscordConnector."""
    config = JarvisConfig()
    engine = MagicMock()
    connector = DiscordConnector(config, engine)
    connector._running = True

    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_channel.id = 5555
    mock_channel.send = AsyncMock()
    mock_client.get_channel.return_value = mock_channel
    connector._client = mock_client

    # Send message
    success = await connector.send_message("5555", "Hello Discord!")
    assert success is True
    mock_channel.send.assert_awaited_with("Hello Discord!", reference=None)

    # Send file
    test_file = tmp_path / "summary.txt"
    test_file.write_text("JARVIS summary report", encoding="utf-8")

    sent = await connector.send_file("5555", test_file, caption="Daily Report")
    assert sent is True
    assert mock_channel.send.await_count == 2
