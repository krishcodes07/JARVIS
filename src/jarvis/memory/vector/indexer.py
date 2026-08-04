"""
Document Indexer — Chunks and indexes documents for vector storage.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Chunks documents and indexes them into the vector store.

    Handles:
    - Text splitting into semantically meaningful chunks
    - Chunk overlap for context preservation
    - Metadata attachment (source, timestamp, etc.)
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks.

        Args:
            text: The text to split.

        Returns:
            List of text chunks.
        """
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        return [c for c in chunks if c]  # Filter empty chunks
