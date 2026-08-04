"""
Embedder — Generates text embeddings using the configured provider.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


class Embedder:
    """Generates text embeddings for vector memory.

    Resolves the embedding provider lazily: the configured ``embedding_provider``
    is preferred (created via the provider manager), otherwise the active chat
    provider is used. If a provider raises ``NotImplementedError`` (e.g. Anthropic
    has no embeddings API), it falls back to the other available provider.
    """

    def __init__(
        self,
        model: str,
        preferred_provider: str | None = None,
        provider_manager: ProviderManager | None = None,
        provider_source: Callable[[], Any] | None = None,
    ) -> None:
        self.model = model
        self._preferred_provider = preferred_provider
        self._provider_manager = provider_manager
        self._provider_source = provider_source
        self._provider: Any | None = None

    def _resolve_provider(self) -> Any:
        """Return a cached provider instance capable of embedding, or raise."""
        if self._provider is not None:
            return self._provider

        if self._provider_manager and self._preferred_provider:
            preferred = self._provider_manager.get_provider(self._preferred_provider)
            if preferred is not None:
                self._provider = preferred
                return preferred

        active = self._provider_source() if self._provider_source else None
        if active is not None:
            self._provider = active
            return active

        raise RuntimeError(
            "No provider available for embeddings. "
            f"Configured embedding_provider='{self._preferred_provider}' has no API key."
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: Texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            RuntimeError: If no usable provider is available.
        """
        provider = self._resolve_provider()
        try:
            return await provider.embed(texts, self.model)
        except NotImplementedError:
            active = self._provider_source() if self._provider_source else None
            if active is not None and active is not provider:
                logger.warning(
                    "Provider does not support embeddings; falling back to active provider."
                )
                self._provider = active
                return await active.embed(texts, self.model)
            raise

    async def embed_single(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        results = await self.embed([text])
        return results[0]
