"""
Base UI — Abstract interface for all JARVIS user interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig


class BaseUI(ABC):
    """Abstract base class for JARVIS user interfaces.

    All UIs (TUI, Web, GUI) implement this interface.
    """

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config

    @abstractmethod
    async def start(self) -> None:
        """Start the user interface."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the user interface."""
        ...
