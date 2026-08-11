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
        self._last_used_model: str = ""

    @property
    def last_used_model(self) -> str:
        """Return the model identifier used for the last generation/stream turn."""
        return self._last_used_model

    async def initialize(self) -> None:
        """Initialize the provider manager and load the active provider."""
        self.registry.load()
        active_name = self.config.provider.active
        try:
            await self.switch_provider(active_name)
        except Exception as e:
            logger.warning(f"Could not initialize active provider '{active_name}': {e}")
            connected = self.registry.list_connected()
            if connected:
                for conn_p in connected:
                    try:
                        await self.switch_provider(conn_p.name)
                        self.config.provider.active = conn_p.name
                        if conn_p.default_model:
                            self.config.provider.model = conn_p.default_model
                        logger.info(f"Switched active provider to connected provider '{conn_p.name}'")
                        break
                    except Exception as ex:
                        logger.warning(f"Could not switch to connected provider '{conn_p.name}': {ex}")

    async def switch_provider(self, name: str) -> None:
        """Switch to a different provider.

        Args:
            name: The provider name from providers.json.
        """
        # Close existing provider safely
        old_provider = self._active_provider
        self._active_provider = None

        if old_provider:
            with contextlib.suppress(Exception):
                await old_provider.close()

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
            raise ProviderError("No active provider configured or initialized.")

        if config is None:
            config = GenerationConfig(
                model=self.config.provider.model,
                temperature=self.config.provider.temperature,
                max_tokens=self.config.provider.max_tokens,
                top_p=self.config.provider.top_p,
            )

        self._last_used_model = config.model

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
            raise ProviderError("No active provider configured or initialized.")

        if config is None:
            config = GenerationConfig(
                model=self.config.provider.model,
                temperature=self.config.provider.temperature,
                max_tokens=self.config.provider.max_tokens,
                top_p=self.config.provider.top_p,
            )

        self._last_used_model = config.model

        has_yielded = False
        try:
            async for chunk in self._active_provider.stream(messages, config):
                has_yielded = True
                yield chunk
        except Exception as e:
            logger.error(f"Provider {self._active_name} stream failed: {e}")
            if not has_yielded and self.config.provider.fallback.enabled:
                async for chunk in self._fallback_stream(messages, config):
                    yield chunk
            else:
                raise

    async def shutdown(self) -> None:
        """Shut down the active provider."""
        if self._active_provider:
            await self._active_provider.close()
            self._active_provider = None

    async def get_models(self, provider_name: str | None = None) -> list[dict[str, Any]]:
        """Fetch available models for a provider directly from the models.dev catalog.

        Args:
            provider_name: Provider name to fetch models for. Defaults to active provider.

        Returns:
            List of model dicts containing 'id' and 'name'.
        """
        target_name = provider_name or self._active_name
        if not target_name:
            return []

        try:
            provider_def = self.registry.get(target_name)
            raw_models = provider_def.models or {}
            results: list[dict[str, Any]] = []

            for mid, mdata in raw_models.items():
                mname = mdata.get("name") if isinstance(mdata, dict) else str(mdata)
                results.append({
                    "id": mid,
                    "name": mname or mid,
                    "description": mdata.get("description", "") if isinstance(mdata, dict) else "",
                })

            if results:
                return sorted(results, key=lambda x: str(x["id"]).lower())

            if provider_def.default_model:
                return [{"id": provider_def.default_model, "name": provider_def.default_model}]
        except Exception as e:
            logger.warning(f"Failed to fetch models for provider {target_name}: {e}")

        return []

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
            self._last_used_model = fallback.model
            if not self._active_provider:
                raise ProviderError(f"Fallback provider '{fallback.provider}' could not be initialized.")
            return await self._active_provider.generate(messages, config)
        except Exception as e:
            logger.error(f"Fallback provider also failed: {e}")
            raise ProviderError(f"Both primary and fallback providers failed: {e}") from e
        finally:
            # Restore original provider
            with contextlib.suppress(Exception):
                await self.switch_provider(original_name)

    async def _fallback_stream(
        self,
        messages: list[Message],
        config: GenerationConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Attempt streaming with the fallback provider."""
        fallback = self.config.provider.fallback
        logger.warning(f"Falling back to {fallback.provider} for streaming...")

        original_name = self._active_name
        try:
            await self.switch_provider(fallback.provider)
            config.model = fallback.model
            self._last_used_model = fallback.model
            if not self._active_provider:
                raise ProviderError(f"Fallback provider '{fallback.provider}' could not be initialized.")
            async for chunk in self._active_provider.stream(messages, config):
                yield chunk
        except Exception as e:
            logger.error(f"Fallback provider stream also failed: {e}")
            raise ProviderError(f"Both primary and fallback provider streams failed: {e}") from e
        finally:
            # Restore original provider
            with contextlib.suppress(Exception):
                await self.switch_provider(original_name)

