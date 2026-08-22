"""
Memory Manager — Coordinates all memory subsystems.

Provides a unified interface to:
- Conversation memory (short-term buffer)
- Long-term memory (persistent facts/preferences)
- Vector memory (semantic search / RAG)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.memory.conversation.store import ConversationStore
    from jarvis.memory.long_term.store import LongTermStore
    from jarvis.memory.vector.store import VectorStore

logger = logging.getLogger(__name__)


def _score_of(entry: dict[str, Any]) -> float:
    """Relevance score of a recall hit, defaulting to 0.0 when unscored."""
    score = entry.get("score")
    return float(score) if isinstance(score, (int, float)) else 0.0


class MemoryManager:
    """Unified memory manager for all memory types.

    Coordinates conversation memory, long-term memory, and vector
    memory to provide rich context to the LLM.

    Usage:
        ```python
        manager = MemoryManager(config)
        await manager.initialize()

        # Store a conversation message
        await manager.add_message(session_id, role="user", content="Hello!")

        # Retrieve relevant memories
        context = await manager.get_context(session_id, query="What's my name?")
        ```
    """

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self.conversation: ConversationStore | None = None
        self.long_term: LongTermStore | None = None
        self.vector: VectorStore | None = None
        self._provider_source: Callable[[], Any] | None = None
        self._provider_manager: Any | None = None
        self._extraction_target: tuple[Any, str] | None = None
        self._extraction_error: str | None = None

    @property
    def extraction_error(self) -> str | None:
        """Why the last long-term extraction failed, if it did."""
        return self._extraction_error

    def status(self) -> dict[str, Any]:
        """Return a health summary of every memory subsystem, for logs and the UI."""
        embedder = self.embedder
        return {
            "conversation": self.conversation is not None,
            "long_term": {
                "enabled": self.long_term is not None,
                "provider": self.config.memory.long_term.provider
                or self.config.provider.active,
                "model": self._get_extraction_model() if self.long_term else "",
                "last_error": self._extraction_error,
            },
            "vector": {
                "enabled": self.vector is not None,
                "embedding": embedder.describe() if embedder is not None else None,
            },
        }

    def set_provider_source(self, source: Callable[[], Any]) -> None:
        """Provide a callable that returns the active LLM provider.

        Used by the long-term extractor and the vector embedder to reach
        the provider without holding a reference to it.
        """
        self._provider_source = source

    @property
    def embedder(self) -> Any | None:
        """Get the embedder instance from vector store if available."""
        return self.vector._embedder if self.vector else None

    def set_provider_manager(self, manager: Any) -> None:
        """Provide the provider manager (for named provider lookups).

        Used by the vector embedder to instantiate the configured
        ``embedding_provider`` (e.g. OpenAI) rather than the chat provider.
        """
        self._provider_manager = manager

    def _get_extraction_target(self) -> tuple[Any, str]:
        """Resolve the provider *and* model for long-term extraction together.

        Provider and model must be resolved as a pair: falling back to the
        active chat provider while keeping ``memory.long_term.model`` (which
        belongs to a different provider) produces an unknown-model API error on
        every extraction.

        Returns:
            ``(provider, model)``; provider is ``None`` when none is usable.
        """
        if self._extraction_target is not None:
            return self._extraction_target

        ltm = self.config.memory.long_term
        target: tuple[Any, str] | None = None

        if ltm.provider and self._provider_manager:
            provider = self._provider_manager.get_provider(ltm.provider)
            if provider is not None:
                target = (provider, ltm.model or self.config.provider.model)
            else:
                logger.warning(
                    "Long-term memory provider '%s' has no API key configured; "
                    "using the active chat provider and model instead.",
                    ltm.provider,
                )

        if target is None:
            provider = self._provider_source() if self._provider_source else None
            active_name = getattr(self._provider_manager, "active_name", "")
            # Keep the configured model only if it belongs to the active provider.
            model = (
                ltm.model
                if ltm.model and ltm.provider and ltm.provider == active_name
                else self.config.provider.model
            )
            target = (provider, model)

        if target[0] is not None:
            self._extraction_target = target
        return target

    def _get_extraction_provider(self) -> Any:
        """Return the provider used for long-term memory extraction."""
        return self._get_extraction_target()[0]

    def _get_extraction_model(self) -> str:
        """Return the model used for long-term memory extraction."""
        return self._get_extraction_target()[1]

    async def initialize(self) -> None:
        """Initialize all enabled memory backends."""
        if self.config.memory.conversation.enabled:
            from jarvis.memory.conversation.store import ConversationStore
            self.conversation = ConversationStore(self.config.memory.conversation)
            await self.conversation.initialize()
            logger.info("Conversation memory initialized.")

        if self.config.memory.long_term.enabled:
            from jarvis.memory.long_term.store import LongTermStore
            self.long_term = LongTermStore(self.config.memory.long_term)
            await self.long_term.initialize()
            logger.info("Long-term memory initialized.")

        if self.config.memory.vector.enabled:
            from jarvis.memory.vector.embedder import Embedder
            from jarvis.memory.vector.store import VectorStore

            vcfg = self.config.memory.vector
            embedder = Embedder(
                model=vcfg.embedding_model,
                preferred_provider=vcfg.embedding_provider,
                provider_manager=self._provider_manager,
                provider_source=self._provider_source,
                backend=vcfg.embedding_backend,
            )
            self.vector = VectorStore(vcfg, embedder)
            await self.vector.initialize()
            logger.info("Vector memory initialized (%s).", embedder.describe())

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        **kwargs: Any,
    ) -> None:
        """Add a message to conversation memory.

        Args:
            session_id: The session identifier.
            role: Message role (user, assistant, system, tool).
            content: Message content.
            **kwargs: Additional metadata (e.g. tool_name, args_str).
        """
        if self.conversation:
            msg_data = {
                "role": role,
                "content": content,
                **kwargs,
            }
            await self.conversation.store(session_id, msg_data)

    async def get_context(
        self,
        session_id: str,
        query: str | None = None,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Assemble conversation history plus recalled long-term memories.

        Long-term recall merges semantic (vector) hits with keyword hits from
        the fact store. Vector search returns an empty list rather than raising
        when embeddings are unavailable, so relying on it alone would silently
        yield no memories at all; the keyword store always contributes.

        Args:
            session_id: The session identifier.
            query: The current user query driving recall.
            max_results: Maximum long-term memories to return.

        Returns:
            Dict with ``conversation`` and, when a query is given, ``long_term``.
        """
        context: dict[str, Any] = {}

        if self.conversation:
            context["conversation"] = await self.conversation.retrieve(session_id)

        if self.long_term and query:
            context["long_term"] = await self._recall_long_term(query, max_results)

        return context

    async def _recall_long_term(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Recall long-term memories via vector search merged with keyword search."""
        results: list[dict[str, Any]] = []

        if self.vector:
            try:
                results.extend(await self.vector.search(query, max_results))
            except Exception as e:
                logger.warning(f"Vector memory search failed: {e}")

        if self.long_term:
            try:
                results.extend(await self.long_term.retrieve(query, max_results))
            except Exception as e:
                logger.warning(f"Long-term keyword search failed: {e}")

        # Dedupe on content (the same fact is stored in both backends), keeping
        # the highest-scoring copy, then return the strongest matches overall.
        best: dict[str, dict[str, Any]] = {}
        for entry in results:
            content = str(entry.get("content", "")).strip()
            if not content:
                continue
            key = content.lower()
            previous = best.get(key)
            if previous is None or _score_of(entry) > _score_of(previous):
                best[key] = entry

        ranked = sorted(best.values(), key=_score_of, reverse=True)
        return ranked[: max(1, max_results)]

    async def store_vector(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a document in vector memory for semantic retrieval.

        Args:
            content: The text to store.
            metadata: Optional metadata (e.g. source, category).
        """
        if not self.vector or not content:
            return

        import hashlib

        key = hashlib.sha1(content.encode("utf-8")).hexdigest()[:32]
        try:
            await self.vector.store(key, {"content": content, "metadata": metadata or {}})
        except Exception as e:
            logger.warning(f"Vector memory store failed: {e}")

    async def index_knowledge_base(self) -> int:
        """Chunk and index knowledge base documents into vector memory.

        Reads ``.txt``, ``.md``, and ``.rst`` files from the configured
        knowledge base directory, chunks them, and stores the embeddings.

        Returns:
            Number of chunks indexed.
        """
        if not self.vector:
            return 0

        from jarvis.core.paths import resolve_data_path
        from jarvis.memory.vector.indexer import DocumentIndexer

        kb_dir = resolve_data_path(self.config.memory.vector.knowledge_base_path)
        if not kb_dir.exists():
            return 0

        indexer = DocumentIndexer(
            chunk_size=self.config.memory.vector.chunk_size,
            chunk_overlap=self.config.memory.vector.chunk_overlap,
        )

        total = 0
        for path in sorted(kb_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".rst"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                logger.warning(f"Skipping knowledge base file {path}: {e}")
                continue

            chunks = indexer.chunk_text(text)
            if not chunks:
                continue

            ids = [f"{path.stem}:{i}" for i in range(len(chunks))]
            metadatas = [
                {"source": str(path.relative_to(kb_dir)), "type": "knowledge"}
            ] * len(chunks)
            try:
                await self.vector.add_documents(chunks, ids, metadatas)
            except Exception as e:
                logger.warning(f"Indexing {path} failed: {e}")
                continue
            total += len(chunks)

        if total:
            logger.info(f"Indexed {total} knowledge base chunks.")
        return total

    async def extract_and_store(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract long-term memories from a conversation exchange and store them.

        Uses the active LLM provider (when available) to identify durable facts,
        preferences, and instructions worth remembering.

        Args:
            session_id: The session the messages came from.
            messages: Recent conversation messages (user/assistant turns).

        Returns:
            The list of extracted and stored memories.
        """
        if not self.long_term:
            return []

        provider, model = self._get_extraction_target()
        if provider is None:
            self._extraction_error = (
                "No LLM provider is available for long-term memory extraction. "
                "Configure an API key for the active provider or set "
                "memory.long_term.provider."
            )
            logger.warning(self._extraction_error)
            return []

        from jarvis.memory.long_term.extractor import (
            MemoryExtractionError,
            MemoryExtractor,
        )

        existing = [
            m.get("content", "")
            for m in await self.long_term.list_all()
            if m.get("content")
        ]

        extractor = MemoryExtractor(provider, model=model)
        try:
            memories = await extractor.extract(messages, existing_memories=existing)
        except MemoryExtractionError as e:
            # Surface rather than swallow: a wrong model id here makes long-term
            # memory silently never store anything.
            self._extraction_error = str(e)
            logger.error(
                "Long-term memory extraction is failing (provider=%s, model=%s): %s",
                self.config.memory.long_term.provider or self.config.provider.active,
                model,
                e,
            )
            return []

        self._extraction_error = None

        for memory in memories:
            key = memory.get("key") or memory.get("content", "")[:80]
            content = memory.get("content", "")
            category = memory.get("category", "fact")
            await self.long_term.store(key, {
                "content": content,
                "category": category,
                "source": session_id,
            })
            if self.vector:
                await self.store_vector(
                    content,
                    {
                        "category": category,
                        "type": "long_term",
                        "source": session_id,
                    },
                )

        if memories:
            logger.info(f"Stored {len(memories)} long-term memories from session {session_id}.")
        return memories

    async def flush(self) -> None:
        """Flush all memory backends to persistent storage."""
        if self.conversation:
            await self.conversation.flush()
        if self.long_term:
            await self.long_term.flush()
        if self.vector:
            await self.vector.flush()
        logger.info("All memory backends flushed.")
