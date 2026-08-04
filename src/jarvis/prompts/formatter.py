"""
Message Formatter — Formats messages for different LLM protocols.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.core.constants import Protocol
from jarvis.providers.base import Message

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats conversation messages for different LLM API protocols."""

    @staticmethod
    def format_for_protocol(
        messages: list[Message],
        protocol: Protocol,
    ) -> list[dict[str, Any]]:
        """Format messages for a specific protocol.

        Args:
            messages: List of Message objects.
            protocol: Target protocol.

        Returns:
            Protocol-specific message format.
        """
        if protocol == Protocol.OPENAI:
            return [{"role": m.role, "content": m.content} for m in messages]
        elif protocol == Protocol.ANTHROPIC:
            # Anthropic separates system from other messages
            return [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role != "system"
            ]
        elif protocol == Protocol.GOOGLE:
            # Google uses 'model' instead of 'assistant'
            return [
                {
                    "role": "model" if m.role == "assistant" else m.role,
                    "parts": [{"text": m.content if isinstance(m.content, str) else str(m.content)}],
                }
                for m in messages
                if m.role != "system"
            ]
        return [{"role": m.role, "content": m.content} for m in messages]
