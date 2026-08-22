"""
Embedder — Generates text embeddings for vector memory.

Resolves a working embedding backend at runtime rather than trusting configuration:

* ``provider`` — a remote embeddings API (OpenAI, Google, Mistral, NVIDIA…). Used
  only when the configured provider has credentials *and* the configured model is
  actually an embedding model in the models.dev catalog.
* ``local`` — ChromaDB's bundled ONNX ``all-MiniLM-L6-v2``. Needs no API key and
  works offline once downloaded.

The default ``auto`` backend prefers the remote provider and permanently degrades
to local on the first failure, so a missing key, a wrong model id or a provider
without an ``/embeddings`` endpoint downgrades quality instead of silently
disabling vector memory altogether.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from jarvis.memory.vector.local_embedder import LocalEmbedder, LocalEmbeddingError

if TYPE_CHECKING:
    from jarvis.providers.manager import ProviderManager

logger = logging.getLogger(__name__)

BACKEND_AUTO = "auto"
BACKEND_LOCAL = "local"
BACKEND_PROVIDER = "provider"


class EmbeddingUnavailableError(RuntimeError):
    """Raised when no embedding backend can be used at all."""


class Embedder:
    """Generates text embeddings, preferring a remote provider and falling back to local."""

    def __init__(
        self,
        model: str,
        preferred_provider: str | None = None,
        provider_manager: ProviderManager | None = None,
        provider_source: Callable[[], Any] | None = None,
        backend: str = BACKEND_AUTO,
        local_embedder: LocalEmbedder | None = None,
    ) -> None:
        self.model = model or ""
        self._preferred_provider = (preferred_provider or "").strip()
        self._provider_manager = provider_manager
        self._provider_source = provider_source
        self._backend = (backend or BACKEND_AUTO).strip().lower()

        self._remote: Any | None = None
        self._remote_checked = False
        self._local = local_embedder or LocalEmbedder()
        # No provider and no model configured is not a misconfiguration: it is
        # the fresh-install default meaning "use the bundled local model".
        # ``backend: provider`` opts out — there it is a real misconfiguration.
        self._local_by_design = (
            not self.model
            and not self._preferred_provider
            and self._backend != BACKEND_PROVIDER
        )
        self._use_local = self._backend == BACKEND_LOCAL or self._local_by_design
        self._last_error: str | None = None
        self._dimension: int | None = None

    # ─── Introspection ────────────────────────────────────────

    @property
    def backend(self) -> str:
        """The configured backend mode (``auto`` | ``local`` | ``provider``)."""
        return self._backend

    @property
    def active_backend(self) -> str:
        """Which backend is actually in use right now."""
        if self._use_local:
            return BACKEND_LOCAL
        if self._remote is not None:
            return BACKEND_PROVIDER
        return self._backend

    @property
    def is_local(self) -> bool:
        """True when embeddings are produced by the bundled offline model."""
        return self._use_local

    @property
    def active_model(self) -> str:
        """The model id that will actually be used for embedding."""
        if self._use_local:
            return self._local.model_name
        return self.model

    @property
    def dimension(self) -> int | None:
        """Embedding dimension, known after the first successful embed."""
        return self._dimension

    @property
    def last_error(self) -> str | None:
        """The most recent embedding failure, if any."""
        return self._last_error

    def describe(self) -> dict[str, Any]:
        """Return a status summary suitable for logs and the UI."""
        return {
            "backend": self.active_backend,
            "configured_backend": self._backend,
            "model": self.active_model,
            "provider": "" if self._use_local else self._preferred_provider,
            "dimension": self._dimension,
            "local_by_design": self._local_by_design,
            "ready": self._local.is_ready() if self._use_local else self._remote is not None,
            "last_error": self._last_error,
        }

    # ─── Backend resolution ───────────────────────────────────

    def _model_is_embedding_capable(self) -> bool:
        """Return True if the configured model is an embedding model per models.dev."""
        if not self.model:
            return False
        try:
            from jarvis.providers.models_dev import is_embedding_model, load_models_dev_cache

            cache = load_models_dev_cache()
            entry = (cache.get(self._preferred_provider, {}).get("models") or {}).get(
                self.model
            )
            if entry is not None:
                return is_embedding_model(self.model, entry)
            # Unknown to the catalog (custom/self-hosted model): trust the name.
            return is_embedding_model(self.model)
        except Exception as e:
            logger.debug("Embedding capability check failed for '%s': %s", self.model, e)
            return True

    def _resolve_remote(self) -> Any | None:
        """Return a remote provider instance capable of embeddings, or None.

        Never substitutes the active chat provider for the configured embedding
        provider: the configured *model* id would not exist there, so the call
        would fail on every request.
        """
        if self._remote is not None:
            return self._remote
        if self._remote_checked:
            return None

        self._remote_checked = True

        if not self.model:
            self._last_error = "No embedding model configured."
            return None

        if not self._model_is_embedding_capable():
            self._last_error = (
                f"'{self.model}' is not an embedding model"
                f"{f' for provider {self._preferred_provider}' if self._preferred_provider else ''}."
            )
            logger.warning("%s Using the local embedding model instead.", self._last_error)
            return None

        provider: Any | None = None
        if self._provider_manager and self._preferred_provider:
            provider = self._provider_manager.get_provider(self._preferred_provider)
            if provider is None:
                self._last_error = (
                    f"Embedding provider '{self._preferred_provider}' has no API key configured."
                )
                logger.warning(
                    "%s Using the local embedding model instead.", self._last_error
                )
                return None
        elif not self._preferred_provider and self._provider_source:
            # No dedicated embedding provider configured: the active chat provider
            # is only usable if the configured model belongs to it, which the
            # capability check above already established as plausible.
            provider = self._provider_source()

        if provider is None:
            self._last_error = "No embedding provider available."
            return None

        self._remote = provider
        return provider

    def _degrade_to_local(self, reason: str) -> None:
        """Permanently switch to the local backend after a remote failure."""
        if self._use_local:
            return
        self._use_local = True
        self._remote = None
        self._last_error = reason
        logger.warning(
            "Remote embeddings unavailable (%s). Falling back to the local model '%s'.",
            reason,
            self._local.model_name,
        )

    # ─── Embedding ────────────────────────────────────────────

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: Texts to embed.

        Returns:
            One embedding vector per input text.

        Raises:
            EmbeddingUnavailableError: If neither backend can produce embeddings.
        """
        if not texts:
            return []

        if not self._use_local and self._backend != BACKEND_LOCAL:
            provider = self._resolve_remote()
            if provider is not None:
                try:
                    vectors = await provider.embed(texts, self.model)
                    if vectors:
                        self._dimension = len(vectors[0])
                        self._last_error = None
                        return vectors
                    self._degrade_to_local("provider returned no embeddings")
                except Exception as e:
                    if self._backend == BACKEND_PROVIDER:
                        self._last_error = str(e)
                        raise EmbeddingUnavailableError(
                            f"Embedding provider '{self._preferred_provider or 'active'}' "
                            f"failed for model '{self.model}': {e}"
                        ) from e
                    self._degrade_to_local(f"{type(e).__name__}: {e}")
            elif self._backend == BACKEND_PROVIDER:
                raise EmbeddingUnavailableError(
                    self._last_error or "No embedding provider available."
                )
            else:
                self._use_local = True

        try:
            vectors = await self._local.embed(texts)
        except LocalEmbeddingError as e:
            self._last_error = str(e)
            raise EmbeddingUnavailableError(
                f"No embedding backend is available: {e}"
            ) from e

        if vectors:
            self._dimension = len(vectors[0])
        return vectors

    async def embed_single(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        results = await self.embed([text])
        return results[0] if results else []

    async def warmup(self) -> bool:
        """Resolve and test the embedding backend up front.

        Returns:
            True if embeddings are working, False otherwise. Never raises.
        """
        try:
            vector = await self.embed_single("warmup")
            return bool(vector)
        except Exception as e:
            self._last_error = str(e)
            logger.warning("Embedding warmup failed: %s", e)
            return False
