"""
Long-Term Memory Store — Persistent fact and preference storage.

Stores key facts, user preferences, and learned information
that persists across conversations.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from jarvis.core.config import resolve_data_path
from jarvis.memory.base import BaseMemory

if TYPE_CHECKING:
    from jarvis.core.config import LongTermMemoryConfig

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Words carrying no retrieval signal, so they don't inflate overlap scores.
_STOPWORDS = frozenset(
    ["a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of", "on", "or", "our", "she", "should", "so", "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "we", "were", "what", "when", "where", "which", "who", "whom", "why", "will", "with", "would", "you", "your"]
)


def _tokenize(text: str) -> list[str]:
    """Split lowercased text into alphanumeric words."""
    return _WORD_RE.findall(text)


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
        self._storage_path = resolve_data_path(config.storage_path) / "memories.json"
        self._memories: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Load existing memories from disk."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self._storage_path.exists():
            try:
                content = self._storage_path.read_text(encoding="utf-8").strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        self._memories = data
                    elif isinstance(data, list):
                        self._memories = {
                            f"mem_{i}": v if isinstance(v, dict) else {"content": str(v)}
                            for i, v in enumerate(data)
                        }
                    else:
                        self._memories = {}
                else:
                    self._memories = {}
                    self._storage_path.write_text("{}", encoding="utf-8")
            except Exception as e:
                logger.warning(
                    f"Failed to read memories from {self._storage_path}: {e}. Initializing empty."
                )
                self._memories = {}
                self._storage_path.write_text("{}", encoding="utf-8")
            logger.info(f"Loaded {len(self._memories)} long-term memories.")
        else:
            self._storage_path.write_text("{}", encoding="utf-8")

    async def store(self, key: str, data: Any) -> None:
        """Store or update a memory.

        Args:
            key: Unique memory key.
            data: Memory data dict with 'content', 'category', etc.
        """
        now = datetime.now(UTC).isoformat()
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

    async def retrieve(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Retrieve memories relevant to a query by keyword overlap.

        Scores each memory on how many of the query's significant words it
        contains, normalized by query length. A whole-query substring match is
        treated as a perfect hit. This is the fallback path used whenever
        semantic (vector) recall is unavailable, so it must degrade gracefully
        rather than requiring an exact phrase match.

        Args:
            query: Search query.
            max_results: Maximum number of memories to return.

        Returns:
            Matching memory entries, most relevant first.
        """
        if not query:
            return []

        query_lower = query.lower()
        terms = {t for t in _tokenize(query_lower) if t not in _STOPWORDS}

        scored: list[tuple[float, dict[str, Any]]] = []
        for key, memory in self._memories.items():
            content = memory.get("content", "")
            if not isinstance(content, str) or not content:
                continue

            content_lower = content.lower()
            if query_lower in content_lower:
                score = 1.0
            elif terms:
                content_terms = set(_tokenize(content_lower))
                overlap = terms & content_terms
                if not overlap:
                    continue
                score = len(overlap) / len(terms)
            else:
                continue

            scored.append((score, {"key": key, "score": round(score, 4), **memory}))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[: max(1, max_results)]]

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
