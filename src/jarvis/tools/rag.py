"""
Tool RAG — Dynamic semantic selection of relevant tools using ChromaDB.

Filters large libraries of tools (built-in + MCP) down to the most relevant
subset for a given user prompt, preventing context window bloat.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.providers.base import ToolDefinition

if TYPE_CHECKING:
    from jarvis.memory.vector.embedder import Embedder

logger = logging.getLogger(__name__)


class ToolRetriever:
    """RAG-based dynamic tool retriever backed by ChromaDB."""

    def __init__(self, embedder: Embedder | None = None, storage_path: str = "data/vector_store") -> None:
        self._embedder = embedder
        self._storage_path = PROJECT_ROOT / storage_path
        self._client = None
        self._collection = None
        self._indexed_count: int = 0

    async def initialize(self) -> None:
        """Initialize ChromaDB client and tool collection."""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self._storage_path))
            self._collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name="jarvis_tools_rag",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Tool RAG retriever initialized at {self._storage_path}")
        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB for Tool RAG: {e}")
            self._client = None
            self._collection = None

    def set_embedder(self, embedder: Embedder) -> None:
        """Set or update the embedder instance."""
        self._embedder = embedder

    async def index_tools(self, tools: list[ToolDefinition]) -> None:
        """Index or update tool definitions in the vector store."""
        if not self._collection or not self._embedder or not tools:
            return

        documents: list[str] = []
        ids: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for tool in tools:
            param_details = []
            if isinstance(tool.parameters, dict):
                props = tool.parameters.get("properties", {})
                for p_name, p_info in props.items():
                    if isinstance(p_info, dict) and p_info.get("description"):
                        param_details.append(f"{p_name} ({p_info['description']})")
                    else:
                        param_details.append(p_name)

            doc_content = (
                f"Tool Name: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters: {', '.join(param_details)}"
            )

            documents.append(doc_content)
            ids.append(f"tool:{tool.name}")
            metadatas.append({"name": tool.name})

        try:
            embeddings = await self._embedder.embed(documents)
            try:
                await asyncio.to_thread(
                    self._collection.upsert,
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
            except Exception as e:
                if "dimension" in str(e).lower() and self._client:
                    logger.warning("Embedding dimension changed. Resetting Tool RAG collection...")
                    await asyncio.to_thread(self._client.delete_collection, name="jarvis_tools_rag")
                    self._collection = await asyncio.to_thread(
                        self._client.get_or_create_collection,
                        name="jarvis_tools_rag",
                        metadata={"hnsw:space": "cosine"},
                    )
                    await asyncio.to_thread(
                        self._collection.upsert,
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                    )
                else:
                    raise
            self._indexed_count = len(tools)
            logger.info(f"Indexed {len(tools)} tools in Tool RAG store.")
        except Exception as e:
            logger.warning(f"Failed to index tools in Tool RAG: {e}")

    async def retrieve(
        self,
        query: str,
        all_tools: list[ToolDefinition],
        top_k: int = 8,
        always_include: list[str] | None = None,
    ) -> list[ToolDefinition]:
        """Retrieve top relevant tools for a user query.

        Args:
            query: The user's input prompt.
            all_tools: Complete list of available ToolDefinition objects.
            top_k: Max number of tools to select dynamically.
            always_include: Tool names that should always be present.

        Returns:
            Filtered list of ToolDefinition objects.
        """
        if not all_tools:
            return []

        # If total tools are already small, return all tools
        if len(all_tools) <= top_k:
            return all_tools

        always_set = set(always_include or [])
        always_tools = [t for t in all_tools if t.name in always_set]

        # Auto re-index if new tools (e.g. dynamically connected MCP tools) were added
        if self._collection and self._embedder and self._indexed_count != len(all_tools):
            await self.index_tools(all_tools)

        if not self._collection or not self._embedder or not query.strip():
            # Fallback if vector store/embedder is unavailable or query is empty
            needed = max(0, top_k - len(always_tools))
            fallback_tools = [t for t in all_tools if t.name not in always_set][:needed]
            return always_tools + fallback_tools

        try:
            query_embedding = await self._embedder.embed([query])
            results = await asyncio.to_thread(
                self._collection.query,
                query_embeddings=query_embedding,
                n_results=min(top_k * 2, len(all_tools)),
                include=["metadatas", "distances"],
            )

            metadatas = (results.get("metadatas") or [[]])[0]
            matched_names = [m.get("name") for m in metadatas if m and "name" in m]

            # Build result list starting with always_include tools
            result_map: dict[str, ToolDefinition] = {t.name: t for t in all_tools}
            selected_tools: list[ToolDefinition] = list(always_tools)
            selected_names: set[str] = {t.name for t in selected_tools}

            for name in matched_names:
                if len(selected_tools) >= top_k:
                    break
                if name and name in result_map and name not in selected_names:
                    selected_tools.append(result_map[name])
                    selected_names.add(name)

            # If top_k not reached, pad with remaining tools
            if len(selected_tools) < top_k:
                for tool in all_tools:
                    if len(selected_tools) >= top_k:
                        break
                    if tool.name not in selected_names:
                        selected_tools.append(tool)
                        selected_names.add(tool.name)

            logger.debug(
                f"Tool RAG selected {len(selected_tools)}/{len(all_tools)} tools for query '{query[:30]}...': "
                f"{[t.name for t in selected_tools]}"
            )
            return selected_tools
        except Exception as e:
            logger.warning(f"Tool RAG query failed: {e}. Falling back to default tools.")
            return all_tools[:top_k]
