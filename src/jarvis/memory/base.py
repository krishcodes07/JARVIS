"""
Base Memory — Abstract interface for all memory backends.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseMemory(ABC):
    """Abstract base class for memory storage backends.

    All memory types (conversation, long-term, vector) implement this.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the memory backend."""
        ...

    @abstractmethod
    async def store(self, key: str, data: Any) -> None:
        """Store data in memory."""
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> Any:
        """Retrieve data from memory."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data from memory."""
        ...

    @abstractmethod
    async def flush(self) -> None:
        """Flush any pending writes to persistent storage."""
        ...
