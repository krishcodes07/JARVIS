"""
Conversation Store — Short-term conversation memory.

Stores messages per session in JSON files.
Supports auto-summarization of older messages.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from jarvis.core.paths import get_sessions_dir
from jarvis.memory.base import BaseMemory

if TYPE_CHECKING:
    from jarvis.core.config import ConversationMemoryConfig

logger = logging.getLogger(__name__)


class ConversationStore(BaseMemory):
    """JSON-backed conversation memory.

    Each session's conversation is stored as a separate JSON file
    in ~/.jarvis/workspace/sessions/{session_id}.json.

    Features:
    - Sliding window buffer (keeps last N messages)
    - Auto-summarization of older messages
    - Session-based isolation
    """

    def __init__(self, config: ConversationMemoryConfig) -> None:
        self.config = config
        self._storage_dir = get_sessions_dir()
        self._buffers: dict[str, list[dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Ensure storage directory exists."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    async def store(self, session_id: str, data: Any) -> None:
        """Add a message to the conversation buffer.

        Args:
            session_id: The session identifier.
            data: Message dict with 'role' and 'content'.
        """
        if session_id not in self._buffers:
            self._buffers[session_id] = await self._load_session(session_id)

        message = {
            **data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._buffers[session_id].append(message)

        # Auto-save
        await self._save_session(session_id)

    async def retrieve(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of message dictionaries.
        """
        if session_id not in self._buffers:
            self._buffers[session_id] = await self._load_session(session_id)

        messages = self._buffers[session_id]

        # Apply sliding window
        max_messages = self.config.max_messages
        if len(messages) > max_messages:
            return messages[-max_messages:]
        return messages

    async def delete(self, session_id: str) -> None:
        """Delete a session's conversation history."""
        self._buffers.pop(session_id, None)
        filepath = self._storage_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()

    async def flush(self) -> None:
        """Persist all in-memory conversations to disk."""
        for session_id in self._buffers:
            await self._save_session(session_id)

    async def list_sessions(self) -> list[str]:
        """List all stored session IDs."""
        return [
            p.stem for p in self._storage_dir.glob("*.json")
        ]

    async def truncate(self, session_id: str, keep_count: int) -> None:
        """Truncate conversation history, keeping only the first *keep_count* messages.

        Useful for reverting messages: removes everything from index
        ``keep_count`` onward and auto-saves.

        Args:
            session_id: The session identifier.
            keep_count: Number of messages to keep from the start.
        """
        if session_id not in self._buffers:
            self._buffers[session_id] = await self._load_session(session_id)

        self._buffers[session_id] = self._buffers[session_id][:keep_count]
        await self._save_session(session_id)

    async def fork(
        self, source_session_id: str, new_session_id: str, keep_count: int
    ) -> None:
        """Create a new session by copying the first *keep_count* messages from *source*.

        The source session is not modified.

        Args:
            source_session_id: Session to copy messages from.
            new_session_id: The new session identifier.
            keep_count: Number of messages to copy from the start.
        """
        if source_session_id not in self._buffers:
            self._buffers[source_session_id] = await self._load_session(source_session_id)

        copied = list(self._buffers[source_session_id][:keep_count])
        self._buffers[new_session_id] = copied
        await self._save_session(new_session_id)

    # ─── Private helpers ──────────────────────────────────────

    async def _load_session(self, session_id: str) -> list[dict[str, Any]]:
        """Load a session from disk."""
        filepath = self._storage_dir / f"{session_id}.json"
        if filepath.exists():
            try:
                content = filepath.read_text(encoding="utf-8").strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return data
                filepath.write_text("[]", encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to load session {session_id}: {e}. Resetting to empty list.")
                filepath.write_text("[]", encoding="utf-8")
        return []

    async def _save_session(self, session_id: str) -> None:
        """Save a session to disk."""
        filepath = self._storage_dir / f"{session_id}.json"
        messages = self._buffers.get(session_id, [])
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
