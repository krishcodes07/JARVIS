"""
Web UI Chat Routes — REST & WebSocket endpoints for real-time messaging.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Track background tasks so they aren't garbage-collected mid-flight.
_background_tasks: set[asyncio.Task] = set()

_engine: JarvisEngine | None = None


def set_engine(engine: JarvisEngine | None) -> None:
    """Set the active JarvisEngine instance for this router module."""
    global _engine
    _engine = engine


def _get_engine() -> JarvisEngine | None:
    """Get the active JarvisEngine instance."""
    return _engine


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str = "success"


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """REST endpoint for sending a message to JARVIS."""
    engine = _get_engine()
    if not engine or not engine._initialized:
        raise RuntimeError("JARVIS Engine is not initialized.")

    response_text = await engine.chat(request.message)
    session_id = engine.session.session_id if engine.session else "default"

    return ChatResponse(response=response_text, session_id=session_id)


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time streaming & tool call notifications."""
    await websocket.accept()
    engine = _get_engine()

    if not engine or not engine._initialized:
        await websocket.send_json({"type": "error", "message": "JARVIS Engine not initialized."})
        await websocket.close()
        return

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            user_msg = data.get("message", "").strip()

            if not user_msg:
                continue

            # Callback when engine executes a tool
            def on_tool_call(tool_name: str, tool_args: dict):
                async def _send() -> None:
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": tool_args,
                    })

                task = asyncio.create_task(_send())
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

            # Dangerous tools are denied unless auto_approve is enabled.
            # (The web UI has no interactive approval flow yet.)
            async def approval_callback(tool_name: str, tool_args: dict) -> bool:
                if engine and engine.config and engine.config.tools:
                    return bool(engine.config.tools.auto_approve)
                return False

            # Signal response start
            await websocket.send_json({"type": "start"})

            try:
                async for chunk in engine.stream_chat(
                    user_msg,
                    on_tool_call=on_tool_call,
                    approval_callback=approval_callback,
                ):
                    await websocket.send_json({"type": "content", "content": chunk})
                await websocket.send_json({"type": "end"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
