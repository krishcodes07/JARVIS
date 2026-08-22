import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.ui.web.routes.chat import set_engine, websocket_chat_endpoint


@pytest.mark.asyncio
async def test_approval_callback_safely_handles_none_config():
    """Ensure approval_callback does not crash when engine.config is None."""
    mock_engine = MagicMock()
    mock_engine._initialized = True
    mock_engine.config = None

    captured_callback = None

    async def mock_stream_chat(msg, session_id=None, on_tool_call=None, approval_callback=None):
        nonlocal captured_callback
        captured_callback = approval_callback
        yield "test chunk"

    mock_engine.stream_chat = mock_stream_chat
    set_engine(mock_engine)

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"message": "hi"}', Exception("Disconnect")]

    with contextlib.suppress(Exception):
        await websocket_chat_endpoint(mock_ws)

    assert captured_callback is not None
    # Now invoke the captured approval_callback
    result = await captured_callback("dangerous_tool", {})
    assert result is False

    set_engine(None)
