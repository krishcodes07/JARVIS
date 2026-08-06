"""
JARVIS Session — Manages a single interaction session.

A session tracks the current conversation, active tools, and state
for one continuous interaction with the user.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class Session:
    """Represents a single interaction session with JARVIS.

    A session encapsulates:
    - A unique session ID
    - Conversation history for this session
    - Session-level state and metadata
    - Start/end timestamps

    Attributes:
        session_id: Unique identifier for this session.
        engine: Reference to the JARVIS engine.
        created_at: When the session was created.
        metadata: Arbitrary session metadata.
    """

    def __init__(self, engine: JarvisEngine, session_id: str | None = None) -> None:
        self.session_id: str = session_id or uuid.uuid4().hex[:12]
        self.engine = engine
        self.created_at: datetime = datetime.now(UTC)
        self.metadata: dict[str, Any] = {}
        self._active: bool = True

        logger.info(f"Session created: {self.session_id}")

    @property
    def is_active(self) -> bool:
        """Whether this session is still active."""
        return self._active

    async def end(self) -> None:
        """End the session and persist any remaining state."""
        if not self._active:
            return

        logger.info(f"Ending session: {self.session_id}")
        self._active = False

        # TODO: Persist conversation history
        # TODO: Extract long-term memories from this session

    def to_dict(self) -> dict[str, Any]:
        """Serialize session metadata to a dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "active": self._active,
            "metadata": self.metadata,
        }
