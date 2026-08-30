"""
JARVIS Chat API — REST & WebSocket endpoints for real-time messaging, streaming, and tool execution.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import uuid
from typing import Any, cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_background_tasks: set[asyncio.Task] = set()

#: Tool output is echoed to the client for display only; cap it so a large
#: file read can't flood the socket.
MAX_TOOL_RESULT_CHARS = 4000


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message prompt")
    session_id: str | None = Field(default=None, description="Optional session identifier")
    stream: bool = Field(default=False, description="Whether to stream response")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str = "success"


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Standard non-streaming chat completion endpoint."""
    engine = get_engine()
    if not engine or not engine._initialized:
        return ChatResponse(
            response="Error: JARVIS engine is not initialized.",
            session_id=request.session_id or "default",
            status="error",
        )

    session_id = request.session_id or (
        engine.session.session_id if engine.session else "default"
    )

    response_text = await engine.chat(
        request.message,
        session_id=session_id,
    )

    return ChatResponse(response=response_text, session_id=session_id)


@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time streaming, thoughts, and tool call progress."""
    await websocket.accept()
    engine = get_engine()

    if not engine or not engine._initialized:
        await websocket.send_json({"type": "error", "message": "JARVIS Engine not initialized."})
        await websocket.close()
        return

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            user_msg = data.get("message", "").strip()
            session_id = data.get("session_id") or (
                engine.session.session_id if engine.session else "default"
            )

            if not user_msg:
                continue

            def _emit(payload: dict[str, Any]) -> None:
                """Fire-and-forget a WS frame from a synchronous engine callback."""

                async def _send() -> None:
                    try:
                        await websocket.send_json(payload)
                    except Exception:
                        pass

                task = asyncio.create_task(_send())
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

            # Callback when engine starts executing a tool
            def on_tool_call(tool_name: str, tool_args: dict[str, Any]):
                _emit({
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                })

            # Callback when a tool finishes
            def on_tool_result(tool_name: str, result: Any):
                text = result if isinstance(result, str) else str(result)
                failed = text.strip().lower().startswith(("error", "tool error", "traceback"))
                _emit({
                    "type": "tool_error" if failed else "tool_result",
                    "tool": tool_name,
                    "result": text[:MAX_TOOL_RESULT_CHARS],
                    "truncated": len(text) > MAX_TOOL_RESULT_CHARS,
                    "status": "error" if failed else "completed",
                })

            # Auto-approve callback based on configuration
            async def approval_callback(tool_name: str, tool_args: dict[str, Any]) -> bool:
                if engine and engine.config and engine.config.tools:
                    return engine.config.tools.auto_approve
                return False

            # Interactive ask_user callback
            async def ask_user_callback(
                questions: list[dict[str, Any]],
            ) -> dict[str, Any] | str | None:
                prompt_id = f"prompt_{uuid.uuid4().hex[:8]}"
                await websocket.send_json({
                    "type": "ask_user",
                    "prompt_id": prompt_id,
                    "tool": "ask_user",
                    "questions": questions,
                })

                # Await user response
                while True:
                    resp_raw = await websocket.receive_text()
                    resp_json = json.loads(resp_raw)
                    if resp_json.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        continue
                    if resp_json.get("type") == "ask_user_response":
                        val = (
                            resp_json.get("response")
                            if "response" in resp_json
                            else resp_json.get("responses")
                        )
                        return cast(dict[str, Any] | str | None, val)
                    if resp_json.get("type") == "cancel":
                        return None
                    return cast(dict[str, Any] | str | None, resp_json.get("response"))

            # Signal response start
            await websocket.send_json({
                "type": "start",
                "session_id": session_id,
                "model": engine.last_used_model,
            })

            # Pass ask_user_callback if accepted by the engine / mock
            stream_kwargs: dict[str, Any] = {
                "session_id": session_id,
                "on_tool_call": on_tool_call,
                "on_tool_result": on_tool_result,
                "approval_callback": approval_callback,
            }
            sig = inspect.signature(engine.stream_chat)
            if "ask_user_callback" in sig.parameters or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                stream_kwargs["ask_user_callback"] = ask_user_callback

            try:
                async for chunk in engine.stream_chat(user_msg, **stream_kwargs):
                    await websocket.send_json({"type": "content", "content": chunk})
            except Exception as e:
                logger.exception("Error in stream_chat WebSocket flow")
                await websocket.send_json({"type": "error", "message": str(e)})
            finally:
                # Always close the turn
                try:
                    await websocket.send_json({
                        "type": "end",
                        "session_id": session_id,
                        "model": engine.last_used_model,
                    })
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
