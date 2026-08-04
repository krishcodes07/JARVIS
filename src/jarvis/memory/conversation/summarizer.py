"""
Conversation Summarizer — Auto-summarizes older conversation messages.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """Summarizes older conversation messages to save context tokens.

    Uses the active LLM to generate concise summaries of conversation
    segments that have been pushed out of the sliding window.
    """

    async def summarize(self, messages: list[dict[str, Any]]) -> str:
        """Summarize a list of messages into a concise text.

        Args:
            messages: Messages to summarize.

        Returns:
            A summary string.
        """
        # TODO: Implement using the active LLM provider
        # For now, return a simple concatenation
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                parts.append(f"{role}: {content[:100]}")
        return "Summary of earlier conversation:\n" + "\n".join(parts[-5:])
