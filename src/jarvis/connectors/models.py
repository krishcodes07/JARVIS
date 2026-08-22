"""
Connector Data Models — Standardized message schemas and status representations for multi-platform bridges.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class InboundMessage(BaseModel):
    """Normalized incoming message from any messaging platform."""
    connector: str                                     # e.g. "telegram", "discord"
    user_id: str                                       # Unique platform user ID
    chat_id: str                                       # Unique platform chat/channel ID
    username: str | None = None                        # User handle if available
    full_name: str | None = None                       # User display name if available
    text: str                                          # Extracted clean text content
    message_id: str | None = None                      # Platform message ID (for replies)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class OutboundMessage(BaseModel):
    """Normalized outgoing message to be sent to a messaging platform."""
    chat_id: str
    text: str
    reply_to_message_id: str | None = None
    parse_mode: str | None = None                      # "Markdown", "HTML", etc.
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorStatus(BaseModel):
    """Runtime health and status summary of a connector."""
    name: str
    enabled: bool
    running: bool
    connected_at: datetime | None = None
    messages_received: int = 0
    messages_sent: int = 0
    error_count: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
