"""
Unit tests for the JARVIS Web UI host app (jarvis.ui.web.server) and the chat
WebSocket callback wiring.
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from jarvis.api.deps import set_engine
from jarvis.api.routes import chat as chat_module
from jarvis.api.routes.chat import websocket_chat_endpoint
from jarvis.ui.web.server import create_web_app


def _sent_frames(mock_ws: AsyncMock) -> list[dict]:
    """Every payload handed to ``websocket.send_json``, in call order."""
    return [call.args[0] for call in mock_ws.send_json.call_args_list]


async def _flush_emits() -> None:
    """Await the fire-and-forget tasks that ``_emit`` spawns for tool frames."""
    pending = list(chat_module._background_tasks)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


def _streaming_engine(stream_chat) -> MagicMock:
    engine = MagicMock()
    engine._initialized = True
    engine.last_used_model = "test-model"
    engine.session.session_id = "sess-1"
    engine.config.tools.auto_approve = False
    engine.stream_chat = stream_chat
    return engine


# ─────────────────────────── WebSocket callbacks ───────────────────────────


@pytest.mark.asyncio
async def test_approval_callback_safely_handles_none_config():
    """Ensure approval_callback does not crash when engine.config is None."""
    mock_engine = MagicMock()
    mock_engine._initialized = True
    mock_engine.config = None

    captured_callback = None

    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
    ):
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


@pytest.mark.asyncio
async def test_tool_result_is_emitted_so_pills_can_complete():
    """A finished tool must produce a `tool_result` frame.

    Without it the client has no way to move a tool indicator off "running",
    which is exactly the bug this callback was added to fix.
    """

    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
    ):
        on_tool_call("list_files", {"path": "."})
        on_tool_result("list_files", "a.txt\nb.txt")
        yield "Here are the files."

    set_engine(_streaming_engine(mock_stream_chat))

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"message": "ls"}', WebSocketDisconnect()]

    await websocket_chat_endpoint(mock_ws)
    await _flush_emits()

    frames = _sent_frames(mock_ws)
    types = [f["type"] for f in frames]

    assert "start" in types
    assert "content" in types
    assert "tool_call" in types
    assert "end" in types

    result = next(f for f in frames if f["type"] == "tool_result")
    assert result["tool"] == "list_files"
    assert result["result"] == "a.txt\nb.txt"
    assert result["status"] == "completed"
    assert result["truncated"] is False

    set_engine(None)


@pytest.mark.asyncio
async def test_failed_tool_is_emitted_as_tool_error():
    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
    ):
        on_tool_result("read_file", "Error: no such file 'nope.txt'")
        yield "Sorry."

    set_engine(_streaming_engine(mock_stream_chat))

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"message": "read nope.txt"}', WebSocketDisconnect()]

    await websocket_chat_endpoint(mock_ws)
    await _flush_emits()

    frame = next(f for f in _sent_frames(mock_ws) if f["type"] == "tool_error")
    assert frame["tool"] == "read_file"
    assert frame["status"] == "error"

    set_engine(None)


@pytest.mark.asyncio
async def test_oversized_tool_result_is_truncated():
    payload = "x" * (chat_module.MAX_TOOL_RESULT_CHARS + 500)

    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
    ):
        on_tool_result("read_file", payload)
        yield "done"

    set_engine(_streaming_engine(mock_stream_chat))

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"message": "read big"}', WebSocketDisconnect()]

    await websocket_chat_endpoint(mock_ws)
    await _flush_emits()

    frame = next(f for f in _sent_frames(mock_ws) if f["type"] == "tool_result")
    assert len(frame["result"]) == chat_module.MAX_TOOL_RESULT_CHARS
    assert frame["truncated"] is True

    set_engine(None)


@pytest.mark.asyncio
async def test_stream_failure_still_ends_the_turn():
    """An exception mid-stream must not leave the client generating forever."""

    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
    ):
        yield "partial"
        raise RuntimeError("provider exploded")

    set_engine(_streaming_engine(mock_stream_chat))

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = ['{"message": "hi"}', WebSocketDisconnect()]

    await websocket_chat_endpoint(mock_ws)

    types = [f["type"] for f in _sent_frames(mock_ws)]
    assert "error" in types
    assert types[-1] == "end"

    set_engine(None)


# ────────────────────────── SPA hosting / dist gate ──────────────────────────


def test_missing_dist_serves_build_instructions(tmp_path):
    """No built bundle → an actionable page, not the dev-only index.html."""
    app = create_web_app(engine=None, dist_dir=tmp_path / "not-built")
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 503
    assert "npm run build" in response.text
    # Must not reference the Vite dev entrypoint, which 404s when unbundled.
    assert "/src/main.tsx" not in response.text


def test_missing_dist_does_not_shadow_api_routes(tmp_path):
    """The catch-all must leave /api/* alone so unknown endpoints still 404."""
    app = create_web_app(engine=None, dist_dir=tmp_path / "not-built")
    client = TestClient(app)

    response = client.get("/api/definitely-not-a-route")
    assert response.status_code == 404
    assert "npm run build" not in response.text


def test_built_dist_serves_spa_for_client_routes(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>JARVIS SPA</body></html>", encoding="utf-8")

    app = create_web_app(engine=None, dist_dir=dist)
    client = TestClient(app)

    # Both the root and a client-side route fall through to index.html.
    for path in ("/", "/settings/appearance"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "JARVIS SPA" in response.text


def test_built_dist_serves_real_static_files(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")

    client = TestClient(create_web_app(engine=None, dist_dir=dist))

    response = client.get("/favicon.svg")
    assert response.status_code == 200
    assert "svg" in response.text


def test_cli_host_and_port_args(monkeypatch):
    """Ensure --host and --port CLI options parse correctly."""
    from jarvis.__main__ import parse_args
    import sys

    monkeypatch.setattr(sys, "argv", ["jarvis", "--ui", "web", "--port", "8080", "--host", "127.0.0.1"])
    args = parse_args()
    assert args.ui == "web"
    assert args.port == 8080
    assert args.host == "127.0.0.1"


@pytest.mark.asyncio
async def test_websocket_ask_user_flow():
    """Verify WebSocket ask_user prompt frame is emitted and response is returned."""
    received_answer = None

    async def mock_stream_chat(
        msg,
        session_id=None,
        on_tool_call=None,
        on_tool_result=None,
        approval_callback=None,
        ask_user_callback=None,
    ):
        nonlocal received_answer
        assert ask_user_callback is not None
        questions = [{"question": "Choose framework:", "options": ["React", "Vue"]}]
        received_answer = await ask_user_callback(questions)
        yield f"Configured with {received_answer}"

    set_engine(_streaming_engine(mock_stream_chat))

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        '{"message": "Setup project"}',
        '{"type": "ask_user_response", "response": "React"}',
        WebSocketDisconnect(),
    ]

    await websocket_chat_endpoint(mock_ws)
    await _flush_emits()

    frames = _sent_frames(mock_ws)
    types = [f["type"] for f in frames]

    assert "ask_user" in types
    ask_frame = next(f for f in frames if f["type"] == "ask_user")
    assert ask_frame["questions"][0]["question"] == "Choose framework:"
    assert received_answer == "React"

    set_engine(None)

