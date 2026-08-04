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
        self._extraction_provider: Any | None = None
        self._extraction_provider_resolved: bool = False

    def set_provider_source(self, source: Callable[[], Any]) -> None:
        """Provide a callable that returns the active LLM provider.

        Used by the long-term extractor and the vector embedder to reach
        the provider without holding a reference to it.
        """
        self._provider_source = source

    def set_provider_manager(self, manager: Any) -> None:
        """Provide the provider manager (for named provider lookups).

        Used by the vector embedder to instantiate the configured
        ``embedding_provider`` (e.g. OpenAI) rather than the chat provider.
        """
        self._provider_manager = manager

    def _get_extraction_provider(self) -> Any:
        """Return the provider used for long-term memory extraction.

        Uses ``memory.long_term.provider`` if set (cached), otherwise the
        active chat provider.
        """
        ltm = self.config.memory.long_term
        if ltm.provider and self._provider_manager and not self._extraction_provider_resolved:
            self._extraction_provider = self._provider_manager.get_provider(ltm.provider)
            self._extraction_provider_resolved = True
        if self._extraction_provider is not None:
            return self._extraction_provider
        return self._provider_source() if self._provider_source else None

    def _get_extraction_model(self) -> str:
        """Return the model used for long-term memory extraction."""
        ltm = self.config.memory.long_term
        return ltm.model or self.config.provider.model

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

            embedder = Embedder(
                model=self.config.memory.vector.embedding_model,
                preferred_provider=self.config.memory.vector.embedding_provider,
                provider_manager=self._provider_manager,
                provider_source=self._provider_source,
            )
            self.vector = VectorStore(self.config.memory.vector, embedder)
            await self.vector.initialize()
            logger.info("Vector memory initialized.")

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
        context: dict[str, Any] = {}

        if self.conversation:
            context["conversation"] = await self.conversation.retrieve(session_id)

        if self.long_term and query:
            # Prefer semantic (vector) retrieval for long-term memory since it
            # grows over time; fall back to keyword matching without vectors.
            if self.vector:
                try:
                    context["long_term"] = await self.vector.search(query, max_results)
                except Exception as e:
                    logger.warning(f"Vector memory search failed: {e}")
                    context["long_term"] = await self.long_term.retrieve(query)
            else:
                context["long_term"] = await self.long_term.retrieve(query)

        return context

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

        from jarvis.core.config import PROJECT_ROOT
        from jarvis.memory.vector.indexer import DocumentIndexer

        kb_dir = PROJECT_ROOT / self.config.memory.vector.knowledge_base_path
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

        provider = self._get_extraction_provider()
        if provider is None:
            logger.debug("No provider available for memory extraction; skipping.")
            return []

        from jarvis.memory.long_term.extractor import MemoryExtractor

        existing = [
            m.get("content", "")
            for m in await self.long_term.list_all()
            if m.get("content")
        ]

        extractor = MemoryExtractor(provider, model=self._get_extraction_model())
        memories = await extractor.extract(messages, existing_memories=existing)

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
