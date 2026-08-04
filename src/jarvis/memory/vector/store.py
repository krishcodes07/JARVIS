"""
Vector Store — Semantic memory using embeddings for RAG.

Provides vector-based storage and retrieval for:
- Past conversation segments
- Knowledge base documents
- Long-term memory entries
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.memory.base import BaseMemory
from jarvis.memory.vector.embedder import Embedder

if TYPE_CHECKING:
    from jarvis.core.config import VectorMemoryConfig

logger = logging.getLogger(__name__)


class VectorStore(BaseMemory):
    """ChromaDB-backed vector store for semantic memory.

    Uses embeddings to enable semantic search over:
    - Past conversations
    - Knowledge base documents
    - Long-term memory entries

    This powers the RAG (Retrieval-Augmented Generation) pipeline.
    """

    def __init__(self, config: VectorMemoryConfig, embedder: Embedder) -> None:
        self.config = config
        self._embedder = embedder
        self._storage_path = PROJECT_ROOT / config.storage_path
        self._collection = None
        self._client = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
        except ImportError:
            logger.warning(
                "chromadb is not installed. Install it with `pip install chromadb` "
                "to enable vector memory."
            )
            self._client = None
            self._collection = None
            return

        self._client = chromadb.PersistentClient(path=str(self._storage_path))
        self._collection = await asyncio.to_thread(
            self._client.get_or_create_collection,
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Vector store initialized at {self._storage_path}")

    async def store(self, key: str, data: Any) -> None:
        """Store a document with its embedding.

        Args:
            key: Document ID.
            data: Dict with 'content' and optional 'metadata'.
        """
        if self._collection is None:
            return

        content = data.get("content", "") if isinstance(data, dict) else str(data)
        if not content:
            return

        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        embedding = await self._embedder.embed([content])
        await asyncio.to_thread(
            self._collection.upsert,
            ids=[key],
            embeddings=embedding,
            documents=[content],
            metadatas=[_sanitize_metadata(metadata)],
        )
    async def retrieve(self, key: str) -> Any:
        """Retrieve a document by ID."""
        if self._collection is None:
            return None

        result = await asyncio.to_thread(
            self._collection.get,
            ids=[key],
            include=["documents", "metadatas"],
        )
        ids = result.get("ids") or []
        if not ids:
            return None

        return {
            "id": ids[0],
            "content": (result.get("documents") or [""])[0],
            "metadata": (result.get("metadatas") or [{}])[0],
        }

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Semantic search across stored documents.

        Args:
            query: Natural language query.
            max_results: Maximum number of results.

        Returns:
            List of matching documents with similarity scores.
            Returns an empty list if embeddings are unavailable.
        """
        if self._collection is None or not query:
            return []

        try:
            embedding = await self._embedder.embed([query])
        except Exception as e:
            logger.warning(f"Vector search skipped (embedding failed): {e}")
            return []

        result = await asyncio.to_thread(
            self._collection.query,
            query_embeddings=embedding,
            n_results=max_results,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        results: list[dict[str, Any]] = []
        for i, doc_id in enumerate(ids):
            score = None
            if i < len(distances):
                score = round(1.0 - float(distances[i]), 4)
            results.append({
                "id": doc_id,
                "content": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "score": score,
            })
        return results

    async def delete(self, key: str) -> None:
        """Delete a document by ID."""
        if self._collection is None:
            return
        try:
            await asyncio.to_thread(self._collection.delete, ids=[key])
        except Exception as e:
            logger.debug(f"Delete of '{key}' failed (may not exist): {e}")

    async def flush(self) -> None:
        """Persist any pending changes."""
        # ChromaDB handles persistence automatically
        pass

    async def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Batch add documents to the vector store.

        Args:
            documents: List of text documents.
            ids: List of unique IDs for each document.
            metadatas: Optional metadata for each document.
        """
        if self._collection is None or not documents:
            return

        embeddings = await self._embedder.embed(documents)
        clean_metadatas = (
            [_sanitize_metadata(m) for m in metadatas]
            if metadatas
            else [None for _ in documents]
        )
        await asyncio.to_thread(
            self._collection.upsert,
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_metadatas,
        )


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Keep only values ChromaDB accepts (primitives), skipping others.

    Returns ``None`` when nothing remains, since ChromaDB rejects empty dicts.
    """
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        elif isinstance(value, (list, tuple)):
            items = [v for v in value if isinstance(v, (str, int, float, bool))]
            if items:
                clean[key] = items
    return clean if clean else None
