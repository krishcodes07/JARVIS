"""
JARVIS Sessions API — Endpoints for managing, switching, renaming, and deleting conversation sessions.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine
from jarvis.core.paths import get_sessions_dir
from jarvis.core.session import Session
from jarvis.core.snapshot import FileSnapshotManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

#: Sidecar file holding user-assigned session titles. Kept separate from the
#: transcripts so renaming a session can never rewrite conversation history.
TITLES_FILENAME = "_titles.json"


def _titles_path():
    return get_sessions_dir() / TITLES_FILENAME


def _load_titles() -> dict[str, str]:
    """Read the session title sidecar, tolerating a missing/corrupt file."""
    path = _titles_path()
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception as e:
        logger.debug(f"Could not read session titles: {e}")
        return {}


def _save_titles(titles: dict[str, str]) -> None:
    path = _titles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(titles, indent=2, ensure_ascii=False), encoding="utf-8")


def _derive_title(messages: list[dict[str, Any]], fallback: str) -> str:
    """Derive a display title from the first user message."""
    for msg in messages:
        if msg.get("role") == "user":
            content = str(msg.get("content", "")).strip()
            if content:
                return content[:60] + ("..." if len(content) > 60 else "")
    return fallback


class SessionSummary(BaseModel):
    session_id: str
    title: str
    message_count: int
    updated_at: str
    created_at: str
    is_active: bool


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, description="New session title/preview")


class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: str
    status: str = "success"


@router.get("", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    """List all saved conversation sessions sorted by most recently updated."""
    engine = get_engine()
    active_id = engine.session.session_id if (engine and engine.session) else None
    sessions_dir = get_sessions_dir()

    results: list[SessionSummary] = []

    if not sessions_dir.exists():
        return results

    custom_titles = _load_titles()

    for file_path in sessions_dir.glob("*.json"):
        if file_path.name == TITLES_FILENAME:
            continue
        sid = file_path.stem
        try:
            mtime = os.path.getmtime(file_path)
            updated_str = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

            # Read content to get message count and derive a title
            raw = file_path.read_text(encoding="utf-8").strip()
            messages: list[dict[str, Any]] = json.loads(raw) if raw else []

            created_str = updated_str
            if messages and "timestamp" in messages[0]:
                created_str = messages[0]["timestamp"]

            # A user-assigned title always wins over the derived one.
            title = custom_titles.get(sid) or _derive_title(messages, sid)

            results.append(
                SessionSummary(
                    session_id=sid,
                    title=title,
                    message_count=len(messages),
                    updated_at=updated_str,
                    created_at=created_str,
                    is_active=(sid == active_id),
                )
            )
        except Exception as e:
            logger.debug(f"Could not parse session {file_path.name}: {e}")

    # Sort descending by updated_at
    results.sort(key=lambda s: s.updated_at, reverse=True)
    return results


@router.get("/{session_id}")
async def get_session_messages(session_id: str) -> dict[str, Any]:
    """Get full conversation messages for a specific session."""
    sessions_dir = get_sessions_dir()
    file_path = sessions_dir / f"{session_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        raw = file_path.read_text(encoding="utf-8").strip()
        messages = json.loads(raw) if raw else []
        return {
            "session_id": session_id,
            "messages": messages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {e}")


@router.post("/new", response_model=CreateSessionResponse)
async def create_new_session() -> CreateSessionResponse:
    """Create a new session, set it as active on the engine, and return ID."""
    engine = get_engine()
    new_sid = uuid.uuid4().hex[:12]

    if engine:
        engine.session = Session(engine=engine, session_id=new_sid)
        if engine.memory_manager and engine.memory_manager.conversation:
            await engine.memory_manager.conversation.create_session(new_sid)
    else:
        file_path = get_sessions_dir() / f"{new_sid}.json"
        file_path.write_text("[]", encoding="utf-8")

    return CreateSessionResponse(
        session_id=new_sid,
        created_at=datetime.now(UTC).isoformat(),
        status="success",
    )


@router.post("/{session_id}/switch")
async def switch_session(session_id: str) -> dict[str, str]:
    """Switch active session on the engine to this session ID."""
    engine = get_engine()
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")

    engine.session = Session(engine=engine, session_id=session_id)
    return {"status": "success", "session_id": session_id}


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete a session file and clear its file snapshots."""
    sessions_dir = get_sessions_dir()
    file_path = sessions_dir / f"{session_id}.json"

    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete session file: {e}")

    try:
        FileSnapshotManager().clear_session(session_id)
    except Exception:
        pass

    # Drop any user-assigned title so a recycled ID can't inherit it.
    try:
        titles = _load_titles()
        if titles.pop(session_id, None) is not None:
            _save_titles(titles)
    except Exception as e:
        logger.debug(f"Could not prune session title for {session_id}: {e}")

    engine = get_engine()
    if engine and engine.session and engine.session.session_id == session_id:
        engine.session = Session(engine=engine)

    return {"status": "deleted", "session_id": session_id}


@router.post("/{session_id}/rename")
async def rename_session(session_id: str, request: RenameRequest) -> dict[str, str]:
    """Rename a session by recording a display title in the sidecar.

    The conversation transcript is never modified — an earlier implementation
    overwrote the first user message, which silently destroyed history.
    """
    sessions_dir = get_sessions_dir()
    file_path = sessions_dir / f"{session_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    try:
        titles = _load_titles()
        titles[session_id] = title
        _save_titles(titles)
        return {"status": "renamed", "session_id": session_id, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename session: {e}")
