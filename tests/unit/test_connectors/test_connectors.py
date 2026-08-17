"""
Unit tests for JARVIS Connectors subsystem, BaseConnector, TelegramConnector, and ConnectorManager.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.connectors.base import BaseConnector
from jarvis.connectors.manager import ConnectorManager
from jarvis.connectors.models import ConnectorStatus, InboundMessage, OutboundMessage
from jarvis.connectors.telegram.client import TelegramClient, TelegramClientError
from jarvis.connectors.telegram.connector import TelegramConnector
from jarvis.core.config import JarvisConfig


class MockConnector(BaseConnector):
    """Test connector implementation."""
    name: str = "mock"

    def __init__(self, config: JarvisConfig, engine: Any, enabled: bool = True) -> None:
        super().__init__(config, engine)
        self._enabled = enabled
        self.sent_messages: list[dict[str, Any]] = []

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def start(self) -> None:
        self._running = True
        self._connected_at = datetime.now(timezone.utc)

    async def stop(self) -> None:
        self._running = False

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to_message_id: str | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        self.sent_messages.append({
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
            "parse_mode": parse_mode,
        })
        self._messages_sent += 1
        return True


def test_connector_models():
    """Test data models instantiation and default values."""
    inbound = InboundMessage(
        connector="telegram",
        user_id="12345",
        chat_id="99999",
        username="tonystark",
        text="Hello JARVIS",
    )
    assert inbound.connector == "telegram"
    assert inbound.user_id == "12345"
    assert inbound.chat_id == "99999"
    assert inbound.username == "tonystark"
    assert inbound.text == "Hello JARVIS"

    outbound = OutboundMessage(chat_id="99999", text="Hello sir")
    assert outbound.chat_id == "99999"
    assert outbound.text == "Hello sir"

    status = ConnectorStatus(name="telegram", enabled=True, running=True)
    assert status.name == "telegram"
    assert status.enabled
    assert status.running


def test_base_connector_session_id():
    """Test session ID generation for session isolation."""
    config = JarvisConfig()
    engine = MagicMock()
    connector = MockConnector(config, engine)

    session_id = connector.get_session_id("123456")
    assert session_id == "mock_123456"

    session_id_dirty = connector.get_session_id("user:123/chat:456")
    assert session_id_dirty == "mock_user_123_chat_456"


def test_base_connector_allowlist():
    """Test user authorization and allowlist filtering."""
    config = JarvisConfig()
    engine = MagicMock()
    connector = MockConnector(config, engine)

    # Empty allowlist -> allow everyone
    assert connector.is_user_allowed("12345", "user1") is True

    # Configured allowlist
    connector._get_allowed_users = lambda: ["12345", "@tonystark", "bruce_banner"]  # type: ignore

    # Allowed by ID
    assert connector.is_user_allowed("12345", "stranger") is True
    # Allowed by username with @
    assert connector.is_user_allowed("99999", "tonystark") is True
    assert connector.is_user_allowed("99999", "@tonystark") is True
    # Allowed by username without @
    assert connector.is_user_allowed("88888", "bruce_banner") is True

    # Blocked unauthorized user
    assert connector.is_user_allowed("00000", "thanos") is False


def test_base_connector_split_message():
    """Test splitting long messages into chunks."""
    config = JarvisConfig()
    engine = MagicMock()
    connector = MockConnector(config, engine)

    short_text = "Hello world"
    assert connector.split_message(short_text, max_length=100) == ["Hello world"]

    # Long text with paragraphs
    para1 = "A" * 60
    para2 = "B" * 60
    long_text = f"{para1}\n\n{para2}"

    chunks = connector.split_message(long_text, max_length=70)
    assert len(chunks) == 2
    assert chunks[0] == para1
    assert chunks[1] == para2


@pytest.mark.asyncio
async def test_base_connector_builtin_commands():
    """Test handling of /start, /help, /reset, and /status commands."""
    config = JarvisConfig()
    config.jarvis.persona = "iron_man"
    config.provider.model = "gpt-4o"
    config.provider.active = "openai"

    engine = MagicMock()
    engine.config = config
    engine.last_used_model = "gpt-4o"
    engine.tool_registry = []
    engine.mcp_manager = None

    memory_manager = MagicMock()
    conversation_store = MagicMock()
    conversation_store.delete = AsyncMock()
    conversation_store.create_session = AsyncMock()
    conversation_store.list_sessions_info = AsyncMock(return_value=[])
    memory_manager.conversation = conversation_store
    engine.memory_manager = memory_manager

    connector = MockConnector(config, engine)
    connector._running = True

    # /start
    start_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/start")
    start_resp = await connector.handle_builtin_command(start_msg)
    assert start_resp is not None
    assert "Greetings! I am" in start_resp
    assert "gpt-4o" in start_resp

    # /help
    help_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/help")
    help_resp = await connector.handle_builtin_command(help_msg)
    assert help_resp is not None
    assert "/session" in help_resp
    assert "/help" in help_resp

    # /clear / /reset
    reset_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/clear")
    reset_resp = await connector.handle_builtin_command(reset_msg)
    assert reset_resp is not None
    assert "Session Cleared" in reset_resp
    conversation_store.create_session.assert_awaited()

    # /status
    status_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/status")
    status_resp = await connector.handle_builtin_command(status_msg)
    assert status_resp is not None
    assert "JARVIS Engine Status" in status_resp
    assert "openai" in status_resp

    # Regular message -> None
    normal_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="How is the weather?")
    normal_resp = await connector.handle_builtin_command(normal_msg)
    assert normal_resp is None


@pytest.mark.asyncio
async def test_connector_session_commands():
    """Test /session list, /session new, /session load, and /session delete."""
    config = JarvisConfig()
    engine = MagicMock()
    engine.config = config
    engine.last_used_model = "gpt-4o"

    memory_manager = MagicMock()
    conversation_store = MagicMock()
    conversation_store.delete = AsyncMock()
    conversation_store.create_session = AsyncMock()
    conversation_store.retrieve = AsyncMock(return_value=[{"role": "user", "content": "hello"}])
    conversation_store.list_sessions_info = AsyncMock(return_value=[
        {"session_id": "mock_100", "message_count": 5, "title": "Setup Docker", "last_updated": "2026-08-15T12:00:00"},
        {"session_id": "mock_100_work", "message_count": 2, "title": "Fix bug", "last_updated": "2026-08-15T11:00:00"},
    ])
    memory_manager.conversation = conversation_store
    engine.memory_manager = memory_manager

    connector = MockConnector(config, engine)
    connector._running = True

    # 1. /session list
    list_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/session")
    list_resp = await connector.handle_builtin_command(list_msg)
    assert list_resp is not None
    assert "Conversation Sessions" in list_resp
    assert "mock_100" in list_resp
    assert "Setup Docker" in list_resp

    # 2. /session new coding
    new_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/session new coding")
    new_resp = await connector.handle_builtin_command(new_msg)
    assert new_resp is not None
    assert "New Session Created" in new_resp
    assert "mock_100_coding" in new_resp
    assert connector.get_session_id("100") == "mock_100_coding"

    # 3. /session load mock_100
    load_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/session mock_100")
    load_resp = await connector.handle_builtin_command(load_msg)
    assert load_resp is not None
    assert "Active Session Switched" in load_resp
    assert connector.get_session_id("100") == "mock_100"

    # 4. /session delete mock_100_work
    del_msg = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/session delete mock_100_work")
    del_resp = await connector.handle_builtin_command(del_msg)
    assert del_resp is not None
    assert "Session Deleted" in del_resp
    conversation_store.delete.assert_awaited_with("mock_100_work")

    # 5. /new
    shorthand_new = InboundMessage(connector="mock", user_id="1", chat_id="100", text="/new research")
    shorthand_resp = await connector.handle_builtin_command(shorthand_new)
    assert shorthand_resp is not None
    assert "New Session Started" in shorthand_resp
    assert connector.get_session_id("100") == "mock_100_research"


@pytest.mark.asyncio
async def test_connector_models_command():
    """Test /models list, provider switching, and model switching."""
    config = JarvisConfig()
    config.provider.active = "openai"
    config.provider.model = "gpt-4o"

    engine = MagicMock()
    engine.config = config
    engine.last_used_model = "gpt-4o"

    pm = MagicMock()
    mock_p_openai = MagicMock()
    mock_p_openai.name = "openai"
    mock_p_openai.display_name = "OpenAI"
    mock_p_openai.default_model = "gpt-4o"
    mock_p_openai.models = {"gpt-4o": "GPT-4o", "gpt-4o-mini": "GPT-4o Mini"}
    mock_p_openai.is_connected = True
    mock_p_openai.protocol = "openai"

    pm.registry.list_connected.return_value = [mock_p_openai]
    pm.registry.get.return_value = mock_p_openai
    pm.registry.__contains__.side_effect = lambda x: x == "openai"
    pm.get_models = AsyncMock(return_value=[
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
    ])
    pm.switch_provider = AsyncMock()
    engine.provider_manager = pm

    connector = MockConnector(config, engine)
    connector._running = True

    # 1. /model (overview)
    resp = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/model")
    )
    assert resp is not None
    assert "Current Active Model" in resp
    assert "OpenAI" in resp

    # 2. /model list openai
    resp_list = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/model list openai")
    )
    assert resp_list is not None
    assert "Available Models for OpenAI" in resp_list
    assert "gpt-4o-mini" in resp_list

    # 3. /model gpt-4o-mini
    resp_switch = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/model gpt-4o-mini")
    )
    assert resp_switch is not None
    assert "Model Switched to: `gpt-4o-mini`" in resp_switch
    assert config.provider.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_connector_mcp_command():
    """Test /mcp status and /mcp <server> commands."""
    from jarvis.mcp.platform.models import RegisteredTool
    from jarvis.mcp.platform.registry import platform_registry

    config = JarvisConfig()
    config.mcp.enabled = True

    engine = MagicMock()
    engine.config = config

    mcp_mgr = MagicMock()
    mock_manifest = MagicMock()
    mock_manifest.description = "Telegram MCP Bridge"
    mock_manifest.category = "communication"
    mcp_mgr._manifests = {"telegram": mock_manifest}
    mcp_mgr.servers = {"telegram": MagicMock()}
    mcp_mgr.list_available_servers.return_value = [
        {"name": "telegram", "description": "Telegram MCP Bridge", "enabled": True, "configured": True}
    ]
    mcp_mgr.get_available_servers = mcp_mgr.list_available_servers
    engine.mcp_manager = mcp_mgr

    platform_registry.register_tool(
        RegisteredTool(
            name="telegram_send_message",
            qualified_name="telegram__telegram_send_message",
            description="Send a Telegram message",
            server_name="telegram",
        )
    )

    connector = MockConnector(config, engine)
    connector._running = True

    # 1. /mcp (overview)
    resp = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/mcp")
    )
    assert resp is not None
    assert "MCP Servers & Status" in resp
    assert "telegram" in resp
    assert "Connected" in resp

    # 2. /mcp telegram (server details)
    resp_server = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/mcp telegram")
    )
    assert resp_server is not None
    assert "MCP Server" in resp_server
    assert "telegram" in resp_server
    assert "telegram_send_message" in resp_server

    # 3. /mcp connect telegram
    mcp_mgr.connect_server = AsyncMock(return_value=(True, "Connected to telegram (20 tools)"))
    resp_conn = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/mcp connect telegram")
    )
    assert resp_conn is not None
    assert "MCP Server Connected" in resp_conn

    # 4. /mcp disconnect telegram
    mcp_mgr.disconnect_server = AsyncMock(return_value=(True, "Disconnected from telegram"))
    resp_disconn = await connector.handle_builtin_command(
        InboundMessage(connector="mock", user_id="1", chat_id="100", text="/mcp disconnect telegram")
    )
    assert resp_disconn is not None
    assert "MCP Server Disconnected" in resp_disconn


@pytest.mark.asyncio
async def test_telegram_client_url_and_methods():
    """Test TelegramClient methods and payload construction."""
    client = TelegramClient(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    assert client.api_url == "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    with patch.object(client, "_get_client") as mock_get_http:
        mock_http = MagicMock()
        mock_get_http.return_value = mock_http

        # get_me success
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"id": 1, "username": "JarvisBot"}}
        mock_http.get = AsyncMock(return_value=mock_resp)

        bot_info = await client.get_me()
        assert bot_info is not None
        assert bot_info["username"] == "JarvisBot"

        # sendMessage success
        mock_send_resp = MagicMock()
        mock_send_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}
        mock_http.post = AsyncMock(return_value=mock_send_resp)

        sent = await client.send_message(chat_id="100", text="Test message")
        assert sent is not None
        assert sent["message_id"] == 42

    await client.close()


@pytest.mark.asyncio
async def test_telegram_connector_lifecycle_and_message_handling():
    """Test TelegramConnector initialization, update handling, authorization, and AI generation streaming with tool updates."""
    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.telegram.enabled = True
    config.connectors.telegram.bot_token = "mock_token"
    config.connectors.telegram.allowed_users = ["1001", "ironman"]

    engine = MagicMock()

    async def mock_stream(prompt: str, session_id: str = "", on_tool_call=None, on_tool_result=None):
        if on_tool_call:
            await on_tool_call("web_search", {"query": "test"})
        if on_tool_result:
            await on_tool_result("web_search", "result")
        yield "Hello "
        yield "from "
        yield "JARVIS AI."

    engine.stream_chat = mock_stream

    connector = TelegramConnector(config, engine)
    assert connector.is_enabled is True

    with patch.object(connector, "_get_bot_token", return_value="mock_token"):
        with patch("jarvis.connectors.telegram.connector.TelegramClient") as MockClientClass:
            mock_client = MagicMock()
            mock_client.get_me = AsyncMock(return_value={"id": 999, "username": "JarvisAiBot"})
            mock_client.send_message = AsyncMock(return_value={"message_id": 100})
            mock_client.edit_message_text = AsyncMock(return_value={"message_id": 100})
            mock_client.send_chat_action = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            MockClientClass.return_value = mock_client

            await connector.start()
            assert connector.is_running is True

            # Test handling update for authorized user
            update_msg = {
                "message_id": 10,
                "text": "Analyze the codebase",
                "chat": {"id": 200},
                "from": {"id": 1001, "username": "ironman", "first_name": "Tony", "last_name": "Stark"},
            }

            await connector._handle_message_update(update_msg)

            # Verifies initial placeholder was sent
            assert mock_client.send_message.called
            # Verifies tool call edited status and final response edited message
            assert mock_client.edit_message_text.called
            assert connector._messages_received == 1
            assert connector._messages_sent >= 1

            # Test handling update for unauthorized user
            unauthorized_msg = {
                "message_id": 11,
                "text": "Let me in",
                "chat": {"id": 300},
                "from": {"id": 9999, "username": "intruder", "first_name": "Unknown"},
            }

            await connector._handle_message_update(unauthorized_msg)
            # Verifies Access Denied was sent
            last_call = mock_client.send_message.call_args
            assert "Access Denied" in last_call.kwargs.get("text", "") or "Access Denied" in last_call[1].get("text", "")

            await connector.stop()
            assert not connector.is_running


@pytest.mark.asyncio
async def test_connector_manager_startup_and_filtering():
    """Test ConnectorManager discovery, per-connector startup filtering, and lifecycle."""
    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.telegram.enabled = True
    config.connectors.telegram.bot_token = "mock_token"
    config.connectors.discord.enabled = False

    engine = MagicMock()
    manager = ConnectorManager(config, engine)

    # 2 built-in connectors registered
    all_connectors = manager.list_connectors()
    assert len(all_connectors) >= 2
    connector_names = [c.name for c in all_connectors]
    assert "telegram" in connector_names
    assert "discord" in connector_names

    # Only telegram is enabled
    enabled_connectors = manager.list_enabled()
    assert len(enabled_connectors) == 1
    assert enabled_connectors[0].name == "telegram"

    # Mock start for Telegram
    tg_connector = manager.get("telegram")
    assert tg_connector is not None
    tg_connector.start = AsyncMock()
    tg_connector.stop = AsyncMock()

    started = await manager.start_all()
    assert started == ["telegram"]
    tg_connector.start.assert_awaited_once()

    statuses = manager.get_statuses()
    assert len(statuses) >= 2
    tg_status = next(s for s in statuses if s.name == "telegram")
    assert tg_status.enabled is True

    await manager.stop_all()


def test_config_connectors_section():
    """Test config serialization and defaults for connectors."""
    config = JarvisConfig()
    assert hasattr(config, "connectors")
    assert config.connectors.enabled is True
    assert config.connectors.telegram.enabled is False
    assert config.connectors.telegram.polling_timeout == 30
    assert config.connectors.discord.enabled is False


@pytest.mark.asyncio
async def test_engine_initializes_and_shuts_down_connectors():
    """Test that JarvisEngine initializes and shuts down ConnectorManager."""
    from jarvis.core.engine import JarvisEngine

    config = JarvisConfig()
    config.connectors.enabled = True
    config.connectors.telegram.enabled = True
    config.connectors.telegram.bot_token = "mock_token"

    engine = JarvisEngine()

    with patch("jarvis.connectors.manager.TelegramConnector.start", new_callable=AsyncMock) as mock_tg_start:
        with patch("jarvis.connectors.manager.TelegramConnector.stop", new_callable=AsyncMock) as mock_tg_stop:
            async def set_running():
                if engine.connector_manager:
                    conn = engine.connector_manager.get("telegram")
                    if conn:
                        conn._running = True
            mock_tg_start.side_effect = set_running

            with patch("jarvis.core.engine.JarvisEngine._init_providers", new_callable=AsyncMock):
                with patch("jarvis.core.engine.JarvisEngine._init_memory", new_callable=AsyncMock):
                    with patch("jarvis.core.engine.JarvisEngine._init_tools", new_callable=AsyncMock):
                        with patch("jarvis.core.engine.JarvisEngine._init_mcp", new_callable=AsyncMock):
                            with patch("jarvis.core.engine.JarvisEngine._init_voice", new_callable=AsyncMock):
                                await engine.initialize(config)

                                assert engine.connector_manager is not None
                                mock_tg_start.assert_awaited_once()

                                await engine.shutdown()
                                mock_tg_stop.assert_awaited_once()
                                assert engine.connector_manager is None


def test_markdown_to_telegram_html_formatter():
    """Test converting standard markdown to Telegram-safe HTML."""
    from jarvis.connectors.telegram.formatter import markdown_to_telegram_html

    raw_md = """# Title Header
Here is a **bold word** and *italic word*.
Code: `user_id = 123`
Links: [OpenAI](https://openai.com)
Quotes:
> This is a quote.
Lists:
- Item 1
- Item 2
```python
def add(a: int, b: int) -> int:
    return a + b
```
"""
    result = markdown_to_telegram_html(raw_md)
    assert "<b>Title Header</b>" in result
    assert "<b>bold word</b>" in result
    assert "<i>italic word</i>" in result
    assert "<code>user_id = 123</code>" in result
    assert '<a href="https://openai.com">OpenAI</a>' in result
    assert "<blockquote>This is a quote.</blockquote>" in result
    assert "• Item 1" in result
    assert '<pre><code class="language-python">def add(a: int, b: int) -&gt; int:\n    return a + b</code></pre>' in result

    # Test multiple inline code blocks with underscores
    complex_md = "I found the `send_file` tool and `chat_id` parameter. Exclude `sensitive_file.env`."
    complex_res = markdown_to_telegram_html(complex_md)
    assert "<code>send_file</code>" in complex_res
    assert "<code>chat_id</code>" in complex_res
    assert "<code>sensitive_file.env</code>" in complex_res
    assert "INLINE_CODE" not in complex_res


@pytest.mark.asyncio
async def test_telegram_send_file(tmp_path):
    """Test send_file on TelegramConnector."""
    sample_file = tmp_path / "test_report.pdf"
    sample_file.write_bytes(b"%PDF-1.4 test document content")

    config = JarvisConfig()
    engine = MagicMock()
    connector = TelegramConnector(config, engine)
    connector._running = True

    mock_client = MagicMock()
    mock_client.send_file_auto = AsyncMock(return_value={"message_id": 999})
    connector._client = mock_client

    sent = await connector.send_file(
        chat_id="12345",
        file_path=sample_file,
        caption="**Report** generated",
    )
    assert sent is True
    mock_client.send_file_auto.assert_awaited_once()
    assert mock_client.send_file_auto.call_args is not None
    call_kwargs = mock_client.send_file_auto.call_args.kwargs
    assert call_kwargs["chat_id"] == "12345"
    assert "<b>Report</b>" in call_kwargs["caption"]


def test_markdown_to_telegram_html_with_think_tags():
    """Test that <think>...</think> tags are converted to Telegram expandable blockquotes."""
    from jarvis.connectors.telegram.formatter import markdown_to_telegram_html

    raw_text = "<think>Analyzing user query\nChecking files</think>Here is your result:\n- Item A"
    result = markdown_to_telegram_html(raw_text)

    assert "<blockquote expandable>" in result
    assert "💭 <b>Thought</b>" in result
    assert "Analyzing user query" in result
    assert "Checking files" in result
    assert "</blockquote>" in result
    assert "Here is your result:" in result
    assert "• Item A" in result


def test_markdown_to_telegram_html_with_salted_think_tags():
    """Test that salted <think:hash>...</think:hash> tags are converted without leaking hashes."""
    from jarvis.connectors.telegram.formatter import markdown_to_telegram_html

    raw_text = "<think:6124c78e>Checking rain alert status</think:6124c78e>Yes, sir – there is a rain alert."
    result = markdown_to_telegram_html(raw_text)

    assert "<blockquote expandable>" in result
    assert "💭 <b>Thought</b>" in result
    assert "Checking rain alert status" in result
    assert "</blockquote>" in result
    assert "Yes, sir – there is a rain alert." in result
    assert "6124c78e" not in result



@pytest.mark.asyncio
async def test_telegram_connector_thinking_status_update():
    """Test that TelegramConnector updates placeholder message to Thinking... when AI thinks."""
    config = JarvisConfig()
    config.connectors.telegram.enabled = True
    config.connectors.telegram.bot_token = "mock_token"

    engine = MagicMock()

    # Async generator simulating streaming with <think> tag
    async def mock_stream(text, session_id=None, on_tool_call=None, on_tool_result=None):
        yield "<th"
        yield "ink>Step 1: check time."
        yield "</think>"
        yield "It is 8:30 AM."

    engine.stream_chat = mock_stream

    connector = TelegramConnector(config, engine)
    connector._running = True

    mock_client = MagicMock()
    mock_client.send_message = AsyncMock(return_value={"message_id": 101})
    mock_client.edit_message_text = AsyncMock(return_value={"message_id": 101})
    connector._client = mock_client

    incoming_msg = {
        "message_id": 55,
        "chat": {"id": 12345},
        "from": {"id": 1, "username": "krish"},
        "text": "What time is it?",
    }

    await connector._handle_message_update(incoming_msg)

    # Status message was created
    mock_client.send_message.assert_awaited()

    # Edited to Thinking... and finally to response
    edit_calls = mock_client.edit_message_text.await_args_list
    assert len(edit_calls) >= 2

    # Check that one edit was "Thinking..."
    edit_texts = [call.kwargs.get("text") for call in edit_calls]
    assert any("Thinking..." in (t or "") for t in edit_texts)

    # Final edit contains formatted response with expandable thought
    final_edit_text = edit_texts[-1]
    assert final_edit_text is not None
    assert "<blockquote expandable>" in final_edit_text
    assert "Step 1: check time." in final_edit_text
    assert "It is 8:30 AM." in final_edit_text


def test_markdown_to_telegram_html_tables():
    """Test that Markdown tables are converted to aligned monospace <pre><code> blocks."""
    from jarvis.connectors.telegram.formatter import markdown_to_telegram_html

    table_md = """Structure Breakdown:

| Field | Description |
|---|---|
| Header | Web Search Results for 'your query': |
| Result Number | ### 1., ### 2., etc. |
| Title | The page title (or main heading) |
| URL | Direct link to the source |
| Snippet | Brief excerpt of relevant text from the page |

That's the complete payload."""

    result = markdown_to_telegram_html(table_md)

    assert "Structure Breakdown:" in result
    assert "<pre><code>" in result
    assert "</code></pre>" in result
    assert "Field" in result
    assert "Description" in result
    assert "Header" in result
    assert "Web Search Results for 'your query':" in result
    assert "Result Number" in result
    assert "│" in result
    assert "─┼─" in result
    assert "That's the complete payload." in result


@pytest.mark.asyncio
async def test_telegram_connector_group_mention_and_filtering():
    """Test that TelegramConnector processes mentions in groups and ignores unaddressed chatter."""
    config = JarvisConfig()
    config.connectors.telegram.enabled = True
    config.connectors.telegram.bot_token = "mock_token"

    engine = MagicMock()
    received_prompts = []

    async def mock_stream(prompt, session_id=None, on_tool_call=None, on_tool_result=None):
        received_prompts.append(prompt)
        yield "Sure, I can help!"

    engine.stream_chat = mock_stream

    connector = TelegramConnector(config, engine)
    connector._running = True
    connector._bot_username = "JarvisAiBot"
    connector._bot_id = "999"

    mock_client = MagicMock()
    mock_client.send_message = AsyncMock(return_value={"message_id": 201})
    mock_client.edit_message_text = AsyncMock(return_value={"message_id": 201})
    connector._client = mock_client

    # 1. Unaddressed group chatter -> Ignored
    chatter_msg = {
        "message_id": 1,
        "chat": {"id": -100123, "type": "supergroup"},
        "from": {"id": 55, "username": "alice"},
        "text": "Hey everyone, how is it going?",
    }
    await connector._handle_message_update(chatter_msg)
    assert len(received_prompts) == 0

    # 2. Mentioned in group -> Processed and mention stripped
    mention_msg = {
        "message_id": 2,
        "chat": {"id": -100123, "type": "supergroup"},
        "from": {"id": 55, "username": "alice"},
        "text": "@JarvisAiBot What is quantum computing?",
    }
    await connector._handle_message_update(mention_msg)
    assert len(received_prompts) == 1
    assert received_prompts[0] == "What is quantum computing?"



