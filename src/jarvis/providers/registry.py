"""
Provider Registry — Loads and manages provider definitions from providers.json.

Maps provider names to their protocol implementations and configuration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jarvis.core.config import CONFIG_DIR
from jarvis.core.constants import Protocol
from jarvis.core.exceptions import ProviderNotFoundError

logger = logging.getLogger(__name__)


class ProviderDefinition:
    """A provider's configuration from providers.json."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.name: str = data["name"]
        self.display_name: str = data.get("display_name") or self.name
        self.protocol: Protocol = Protocol(data["protocol"])
        self.base_url: str = data["base_url"]
        self.api_key_env: str = data["api_key_env"]
        self.default_model: str = data.get("default_model") or ""
        self.supports: list[str] = data.get("supports") or []
        self.extra_headers: dict[str, str] = data.get("extra_headers") or {}
        self.raw: dict[str, Any] = data

    def __repr__(self) -> str:
        return f"ProviderDefinition(name={self.name!r}, protocol={self.protocol!r})"


class ProviderRegistry:
    """Registry of all available LLM providers.

    Loads provider definitions from providers.json and provides
    lookup by name. Used by ProviderManager to instantiate the
    correct protocol handler.

    Usage:
        ```python
        registry = ProviderRegistry()
        registry.load()
        provider_def = registry.get("groq")
        ```
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderDefinition] = {}

    def load(self, providers_path: Path | None = None) -> None:
        """Load provider definitions from JSON file.

        Args:
            providers_path: Path to providers.json.
        """
        if providers_path is None:
            providers_path = CONFIG_DIR / "providers.json"

        if not providers_path.exists():
            logger.warning(f"Providers file not found: {providers_path}")
            return

        with open(providers_path, encoding="utf-8") as f:
            data = json.load(f)

        for provider_data in data.get("providers", []):
            definition = ProviderDefinition(provider_data)
            self._providers[definition.name] = definition
            logger.debug(f"Registered provider: {definition.name} ({definition.protocol})")

        logger.info(f"Loaded {len(self._providers)} providers from {providers_path}")

    def get(self, name: str) -> ProviderDefinition:
        """Get a provider definition by name.

        Args:
            name: The provider name (e.g., "groq", "openai").

        Returns:
            The provider definition.

        Raises:
            ProviderNotFoundError: If the provider is not registered.
        """
        if name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{name}' not found. Available: {available}"
            )
        return self._providers[name]

    def get_all(self) -> dict[str, ProviderDefinition]:
        """Get dict of all registered provider definitions."""
        return self._providers

    def list_providers(self) -> list[ProviderDefinition]:
        """Get all registered provider definitions."""
        return list(self._providers.values())

    def list_names(self) -> list[str]:
        """Get all registered provider names."""
        return list(self._providers.keys())

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        return name in self._providers
