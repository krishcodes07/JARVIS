"""
Retriever — Semantic search and retrieval (RAG pipeline).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.memory.vector.store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Semantic retriever for RAG (Retrieval-Augmented Generation).

    Combines vector search with optional reranking to find
    the most relevant context for a given query.
    """

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self._vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents for a query.

        Args:
            query: The search query.
            max_results: Maximum number of results.
            min_score: Minimum similarity score threshold.

        Returns:
            List of matching documents with scores and metadata.
        """
        if self._vector_store is None:
            return []

        results = await self._vector_store.search(query, max_results)

        filtered: list[dict[str, Any]] = []
        for item in results:
            score = item.get("score")
            if score is None or score >= min_score:
                filtered.append(item)
        return filtered
