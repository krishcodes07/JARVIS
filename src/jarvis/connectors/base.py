"""
Base Connector — Abstract base class and standard pipeline for all JARVIS messaging bridges.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.connectors.commands.registry import CommandRegistry
from jarvis.connectors.models import ConnectorStatus, InboundMessage

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for external messaging platform bridges (Telegram, Discord, etc.).

    Standardizes session routing, allowlist security, dynamic bot commands (/session, /new, /clear, /status, /help),
    and message chunking across all chat channels.
    """

    name: str = "base"

    def __init__(self, config: JarvisConfig, engine: JarvisEngine) -> None:
        self.config = config
        self.engine = engine
        self._running: bool = False
        self._connected_at: datetime | None = None
        self._messages_received: int = 0
        self._messages_sent: int = 0
        self._error_count: int = 0
        self._last_error: str | None = None
        self._active_sessions: dict[str, str] = self._load_persisted_sessions()
        self.commands: CommandRegistry = CommandRegistry.create_default()

    def _load_persisted_sessions(self) -> dict[str, str]:
        """Load persisted chat -> session mappings from disk."""
        import json
        from jarvis.core.paths import get_jarvis_home
        mapping_file = get_jarvis_home() / "workspace" / "connector_sessions.json"
        if mapping_file.exists():
            try:
                data = json.loads(mapping_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
            except Exception as e:
                logger.debug(f"Failed to load connector_sessions.json: {e}")
        return {}

    def _save_persisted_sessions(self) -> None:
        """Save chat -> session mappings to disk."""
        import json
        from jarvis.core.paths import get_jarvis_home
        mapping_file = get_jarvis_home() / "workspace" / "connector_sessions.json"
        try:
            mapping_file.parent.mkdir(parents=True, exist_ok=True)
            mapping_file.write_text(json.dumps(self._active_sessions, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save connector_sessions.json: {e}")

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check whether this connector is enabled in configuration."""
        ...

    @property
    def is_running(self) -> bool:
        """Return whether the connector background listener is active."""
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start the connector listener (polling or webhook server)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the connector listener gracefully."""
        ...

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to_message_id: str | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send a message to the target platform chat."""
        ...

    async def send_file(
        self,
        chat_id: str,
        file_path: str | Path,
        caption: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> bool:
        """Send a file/image/video to the target platform chat."""
        return False

    def get_session_id(self, chat_id: str | int) -> str:
        """Get the current active session identifier for this chat.

        Defaults to '{connector_name}_{chat_id}' if not switched via /session or /new.
        """
        clean_chat_id = str(chat_id).strip().replace(":", "_").replace("/", "_")
        default_id = f"{self.name}_{clean_chat_id}"
        return self._active_sessions.get(str(chat_id), default_id)

    def set_session_id(self, chat_id: str | int, session_id: str) -> None:
        """Set the active conversation session for this chat and persist to disk."""
        self._active_sessions[str(chat_id)] = session_id.strip()
        self._save_persisted_sessions()

    def is_user_allowed(self, user_id: str | int, username: str | None = None) -> bool:
        """Validate whether a user is authorized to use this bridge based on allowed_users whitelist.

        If allowed_users is empty, all users are permitted.
        """
        allowed = self._get_allowed_users()
        if not allowed:
            return True

        u_id_str = str(user_id).strip().lower()
        u_name = (username or "").strip().lower().lstrip("@")

        for item in allowed:
            item_str = str(item).strip().lower().lstrip("@")
            if item_str == u_id_str or (u_name and item_str == u_name):
                return True

        return False

    def _get_allowed_users(self) -> list[str | int]:
        """Fetch allowed_users list from connector config."""
        return []

    async def handle_builtin_command(self, msg: InboundMessage) -> str | None:
        """Dispatch message to registered command handler if starting with slash.

        Returns:
            Formatted response text if handled, or None if regular user message.
        """
        return await self.commands.dispatch(msg, self, self.engine)

    def split_message(self, text: str, max_length: int = 4000) -> list[str]:
        """Split a long response into multiple clean chunks respecting paragraph and line boundaries.

        Args:
            text: Full text to split.
            max_length: Maximum allowed characters per chunk (e.g. 4000 for Telegram).

        Returns:
            List of text chunks.
        """
        if not text:
            return [""]

        if len(text) <= max_length:
            return [text]

        chunks: list[str] = []
        remaining = text

        while len(remaining) > max_length:
            split_pos = -1

            # Try to split at paragraph boundary (\n\n)
            last_para = remaining[:max_length].rfind("\n\n")
            if last_para > max_length // 2:
                split_pos = last_para + 2
            else:
                # Try single line break (\n)
                last_line = remaining[:max_length].rfind("\n")
                if last_line > max_length // 3:
                    split_pos = last_line + 1
                else:
                    # Try space
                    last_space = remaining[:max_length].rfind(" ")
                    if last_space > max_length // 3:
                        split_pos = last_space + 1
                    else:
                        split_pos = max_length

            chunk = remaining[:split_pos].strip()
            if chunk:
                chunks.append(chunk)
            remaining = remaining[split_pos:].lstrip()

        if remaining:
            chunks.append(remaining)

        return chunks

    def get_status(self) -> ConnectorStatus:
        """Get standard runtime status object."""
        return ConnectorStatus(
            name=self.name,
            enabled=self.is_enabled,
            running=self._running,
            connected_at=self._connected_at,
            messages_received=self._messages_received,
            messages_sent=self._messages_sent,
            error_count=self._error_count,
            last_error=self._last_error,
        )
