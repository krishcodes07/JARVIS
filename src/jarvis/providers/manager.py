"""
Provider Manager — Manages active provider, switching, and fallback.

Responsible for:
- Instantiating the correct protocol handler for the active provider
- Switching between providers at runtime
- Falling back to backup provider on failures
"""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from jarvis.core.constants import Protocol
from jarvis.core.exceptions import ProviderAuthError, ProviderError
from jarvis.providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResponse,
    Message,
    StreamChunk,
)
from jarvis.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages LLM provider lifecycle and routing.

    Usage:
        ```python
        manager = ProviderManager(config)
        await manager.initialize()
        response = await manager.generate(messages, gen_config)
        ```
    """

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self.registry = ProviderRegistry()
        self._active_provider: BaseProvider | None = None
        self._active_name: str = ""

    async def initialize(self) -> None:
        """Initialize the provider manager and load the active provider."""
        self.registry.load()
        active_name = self.config.provider.active
        await self.switch_provider(active_name)

    async def switch_provider(self, name: str) -> None:
        """Switch to a different provider.

        Args:
            name: The provider name from providers.json.
        """
        # Close existing provider
        if self._active_provider:
            await self._active_provider.close()

        provider_def = self.registry.get(name)

        # Get API key
        api_key = os.getenv(provider_def.api_key_env, "")
        if not api_key:
            raise ProviderAuthError(
                f"API key not set. Set the {provider_def.api_key_env} environment variable."
            )

        # Instantiate the correct protocol handler
        self._active_provider = self._create_protocol(
            protocol=provider_def.protocol,
            api_key=api_key,
            base_url=provider_def.base_url,
            extra_headers=provider_def.extra_headers,
        )
        self._active_name = name
        logger.info(f"Switched to provider: {name} ({provider_def.protocol})")

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResponse:
        """Generate a response using the active provider.

        Includes automatic fallback on failure if configured.
        """
        if not self._active_provider:
            raise ProviderError("No active provider. Call initialize() first.")

        if config is None:
            config = GenerationConfig(
                model=self.config.provider.model,
                temperature=self.config.provider.temperature,
                max_tokens=self.config.provider.max_tokens,
                top_p=self.config.provider.top_p,
            )

        try:
            return await self._active_provider.generate(messages, config)
        except Exception as e:
            logger.error(f"Provider {self._active_name} failed: {e}")
            if self.config.provider.fallback.enabled:
                return await self._fallback_generate(messages, config)
            raise

    async def stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response using the active provider."""
        if not self._active_provider:
            raise ProviderError("No active provider. Call initialize() first.")

        if config is None:
            config = GenerationConfig(
                model=self.config.provider.model,
                temperature=self.config.provider.temperature,
                max_tokens=self.config.provider.max_tokens,
                top_p=self.config.provider.top_p,
            )

        async for chunk in self._active_provider.stream(messages, config):
            yield chunk

    async def shutdown(self) -> None:
        """Shut down the active provider."""
        if self._active_provider:
            await self._active_provider.close()
            self._active_provider = None

    async def get_models(self, provider_name: str | None = None) -> list[dict[str, Any]]:
        """Fetch available models dynamically from the provider's /models API endpoint.

        Args:
            provider_name: Provider name to fetch models for. Defaults to active provider.

        Returns:
            List of model dicts containing 'id' and 'name'.
        """
        target_name = provider_name or self._active_name
        if target_name == self._active_name and self._active_provider:
            try:
                return await self._active_provider.list_models()
            except Exception as e:
                logger.warning(f"Failed to fetch active provider models: {e}")

        provider_def = self.registry.get(target_name)
        api_key = os.getenv(provider_def.api_key_env, "")
        if not api_key:
            return [{"id": provider_def.default_model, "name": provider_def.default_model}]

        temp_provider = self._create_protocol(
            protocol=provider_def.protocol,
            api_key=api_key,
            base_url=provider_def.base_url,
            extra_headers=provider_def.extra_headers,
        )
        try:
            return await temp_provider.list_models()
        except Exception as e:
            logger.warning(f"Failed to fetch models for provider {target_name}: {e}")
            return [{"id": provider_def.default_model, "name": provider_def.default_model}]
        finally:
            await temp_provider.close()

    def get_provider(self, name: str) -> BaseProvider | None:
        """Return a protocol instance for a named provider without switching.

        Useful for auxiliary tasks like embeddings that may use a different
        provider than the active chat provider.

        Args:
            name: The provider name from providers.json.

        Returns:
            A configured provider instance, or ``None`` if the provider is
            unknown or its API key is not set.
        """
        try:
            provider_def = self.registry.get(name)
        except ProviderError:
            return None

        api_key = os.getenv(provider_def.api_key_env, "")
        if not api_key:
            return None

        return self._create_protocol(
            protocol=provider_def.protocol,
            api_key=api_key,
            base_url=provider_def.base_url,
            extra_headers=provider_def.extra_headers,
        )

    @property
    def active_name(self) -> str:
        """Name of the currently active provider."""
        return self._active_name

    @property
    def active_provider(self) -> BaseProvider | None:
        """The currently active provider protocol instance."""
        return self._active_provider

    # ─── Private ──────────────────────────────────────────────

    def _create_protocol(
        self,
        protocol: Protocol,
        api_key: str,
        base_url: str,
        extra_headers: dict[str, str] | None = None,
    ) -> BaseProvider:
        """Instantiate the correct protocol handler."""
        if protocol == Protocol.OPENAI:
            from jarvis.providers.protocols.openai import OpenAIProvider
            return OpenAIProvider(
                api_key=api_key, base_url=base_url, extra_headers=extra_headers
            )
        elif protocol == Protocol.ANTHROPIC:
            from jarvis.providers.protocols.anthropic import AnthropicProvider
            return AnthropicProvider(
                api_key=api_key, base_url=base_url, extra_headers=extra_headers
            )
        elif protocol == Protocol.GOOGLE:
            from jarvis.providers.protocols.google import GoogleProvider
            return GoogleProvider(
                api_key=api_key, base_url=base_url, extra_headers=extra_headers
            )
        else:
            raise ProviderError(f"Unknown protocol: {protocol}")

    async def _fallback_generate(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> GenerationResponse:
        """Attempt generation with the fallback provider."""
        fallback = self.config.provider.fallback
        logger.warning(f"Falling back to {fallback.provider}...")

        original_name = self._active_name
        try:
            await self.switch_provider(fallback.provider)
            config.model = fallback.model
            return await self._active_provider.generate(messages, config)
        except Exception as e:
            logger.error(f"Fallback provider also failed: {e}")
            raise ProviderError(f"Both primary and fallback providers failed: {e}") from e
        finally:
            # Restore original provider
            with contextlib.suppress(Exception):
                await self.switch_provider(original_name)
