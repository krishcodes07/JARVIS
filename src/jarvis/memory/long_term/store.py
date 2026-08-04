"""
Long-Term Memory Store — Persistent fact and preference storage.

Stores key facts, user preferences, and learned information
that persists across conversations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.memory.base import BaseMemory

if TYPE_CHECKING:
    from jarvis.core.config import LongTermMemoryConfig

logger = logging.getLogger(__name__)


class LongTermStore(BaseMemory):
    """JSON-backed long-term memory store.

    Stores structured facts and preferences extracted from conversations.
    Each memory entry has:
    - key: Unique identifier
    - content: The memory content
    - category: Type of memory (fact, preference, instruction)
    - created_at: When it was created
    - updated_at: When it was last updated
    - source: Where it came from (session ID)
    """

    def __init__(self, config: LongTermMemoryConfig) -> None:
        self.config = config
        self._storage_path = PROJECT_ROOT / config.storage_path / "memories.json"
        self._memories: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Load existing memories from disk."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self._storage_path.exists():
            with open(self._storage_path, encoding="utf-8") as f:
                self._memories = json.load(f)
            logger.info(f"Loaded {len(self._memories)} long-term memories.")

    async def store(self, key: str, data: Any) -> None:
        """Store or update a memory.

        Args:
            key: Unique memory key.
            data: Memory data dict with 'content', 'category', etc.
        """
        now = datetime.now(timezone.utc).isoformat()
        if key in self._memories:
            self._memories[key].update(data)
            self._memories[key]["updated_at"] = now
        else:
            self._memories[key] = {
                **data,
                "created_at": now,
                "updated_at": now,
            }
        await self._persist()

    async def retrieve(self, query: str) -> list[dict[str, Any]]:
        """Retrieve memories relevant to a query.

        Simple keyword matching for now. Will be enhanced with
        semantic search via vector memory.

        Args:
            query: Search query.

        Returns:
            List of matching memory entries.
        """
        query_lower = query.lower()
        results = []
        for key, memory in self._memories.items():
            content = memory.get("content", "")
            if isinstance(content, str) and query_lower in content.lower():
                results.append({"key": key, **memory})
        return results

    async def delete(self, key: str) -> None:
        """Delete a memory by key."""
        self._memories.pop(key, None)
        await self._persist()

    async def flush(self) -> None:
        """Persist memories to disk."""
        await self._persist()

    async def list_all(self) -> list[dict[str, Any]]:
        """List all stored memories."""
        return [{"key": k, **v} for k, v in self._memories.items()]

    async def _persist(self) -> None:
        """Write memories to JSON file."""
        with open(self._storage_path, "w", encoding="utf-8") as f:
            json.dump(self._memories, f, indent=2, ensure_ascii=False)
