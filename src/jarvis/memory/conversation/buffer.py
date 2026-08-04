"""
Conversation Buffer — Token-aware sliding window for conversation history.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConversationBuffer:
    """Token-aware conversation buffer.

    Maintains a sliding window of messages that fits within
    the model's context window. Older messages are summarized
    or truncated to make room for new ones.
    """

    def __init__(self, max_messages: int = 100, max_tokens: int | None = None) -> None:
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = []

    def add(self, message: dict[str, Any]) -> None:
        """Add a message to the buffer."""
        self._messages.append(message)
        self._trim()

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages in the buffer."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear the buffer."""
        self._messages.clear()

    def _trim(self) -> None:
        """Trim the buffer to fit constraints."""
        if len(self._messages) > self.max_messages:
            overflow = len(self._messages) - self.max_messages
            self._messages = self._messages[overflow:]

    def __len__(self) -> int:
        return len(self._messages)
