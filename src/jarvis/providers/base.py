"""
Base Provider — Abstract interface for all LLM providers.

All provider protocols must implement this interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """A single message in a conversation."""
    role: str
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolDefinition(BaseModel):
    """A tool definition for function calling."""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    category: str = "basic"
    keywords: list[str] = Field(default_factory=list)


class GenerationConfig(BaseModel):
    """Generation parameters for LLM requests."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[ToolDefinition] | None = None


class GenerationResponse(BaseModel):
    """Normalized response from any LLM provider."""
    content: str = ""
    role: str = "assistant"
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """A single chunk from a streaming response."""
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str | None = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers.

    Every protocol implementation (OpenAI, Anthropic, Google) must
    subclass this and implement all abstract methods.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.extra_headers = extra_headers or {}

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> GenerationResponse:
        """Generate a response from the LLM.

        Args:
            messages: Conversation history.
            config: Generation parameters.

        Returns:
            Normalized generation response.
        """
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the LLM.

        Args:
            messages: Conversation history.
            config: Generation parameters.

        Yields:
            Stream chunks as they arrive.
        """
        ...

    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate embeddings for the given texts.

        Args:
            texts: List of texts to embed.
            model: Embedding model ID.

        Returns:
            List of embedding vectors.
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """Fetch available models dynamically from the provider API.

        Returns:
            List of model dictionaries containing at least 'id' and 'name'.
        """
        ...

    async def close(self) -> None:
        """Clean up resources (close HTTP clients, etc.)."""
        pass
