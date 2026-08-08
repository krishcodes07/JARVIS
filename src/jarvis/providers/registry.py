"""
Provider Registry — Loads and manages provider definitions from models.dev database.

Maps provider names to their protocol implementations and configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jarvis.core.constants import Protocol
from jarvis.core.exceptions import ProviderNotFoundError
from jarvis.providers.models_dev import (
    get_provider_base_url,
    get_provider_env_var,
    get_provider_protocol,
    is_provider_connected,
    load_models_dev_cache,
)

logger = logging.getLogger(__name__)


class ProviderDefinition:
    """A provider's configuration derived from models.dev catalog or custom config."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.name: str = data["name"]
        self.display_name: str = data.get("display_name") or data.get("name") or self.name
        self.protocol: Protocol = (
            Protocol(data["protocol"]) if isinstance(data.get("protocol"), str) else data.get("protocol", Protocol.OPENAI)
        )
        self.base_url: str = data.get("base_url") or ""
        self.api_key_env: str = data.get("api_key_env") or ""
        self.default_model: str = data.get("default_model") or ""
        self.supports: list[str] = data.get("supports") or ["text", "streaming", "tools"]
        self.extra_headers: dict[str, str] = data.get("extra_headers") or {}
        self.models: dict[str, Any] = data.get("models") or {}
        self.raw: dict[str, Any] = data

    @property
    def is_connected(self) -> bool:
        """Return True if an API key is set for this provider."""
        return is_provider_connected(self.name, self.raw)

    def __repr__(self) -> str:
        return f"ProviderDefinition(name={self.name!r}, protocol={self.protocol!r})"


class ProviderRegistry:
    """Registry of all available LLM providers from models.dev.

    Loads provider definitions and provides lookup by name. Used by ProviderManager
    to instantiate protocol handlers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderDefinition] = {}

    def load(self, providers_path: Path | None = None) -> None:
        """Load provider definitions from models.dev catalog cache."""
        data = load_models_dev_cache()
        if not data:
            logger.warning("models.dev cache empty, loading standard defaults.")

        self._providers.clear()
        for pid, pdata in data.items():
            display_name = pdata.get("name") or pid
            env_var = get_provider_env_var(pid, pdata)
            base_url = get_provider_base_url(pid, pdata)
            protocol = get_provider_protocol(pid, pdata)
            models_dict = pdata.get("models") or {}
            default_model = list(models_dict.keys())[0] if models_dict else ""

            p_def = ProviderDefinition({
                "name": pid,
                "display_name": display_name,
                "protocol": protocol,
                "base_url": base_url,
                "api_key_env": env_var,
                "default_model": default_model,
                "supports": ["text", "streaming", "tools"],
                "models": models_dict,
                "raw": pdata,
            })
            self._providers[pid] = p_def

        logger.info(f"Loaded {len(self._providers)} providers into ProviderRegistry from models.dev catalog")

    def get(self, name: str) -> ProviderDefinition:
        """Get a provider definition by name (case-insensitive with alias resolution)."""
        clean = name.strip().lower()
        if clean in self._providers:
            return self._providers[clean]

        clean_alt = clean.replace("_", "-")
        if clean_alt in self._providers:
            return self._providers[clean_alt]

        # 1. Exact display_name match
        for k, v in self._providers.items():
            if v.display_name.lower() == clean or v.display_name.lower() == clean_alt:
                return v

        # 2. Substring & alias matching (e.g. 'opencode-zen' -> 'opencode')
        for k, v in self._providers.items():
            k_clean = k.lower()
            v_disp = v.display_name.lower()
            if (
                clean in k_clean
                or k_clean in clean
                or clean in v_disp
                or v_disp in clean
                or clean.replace("-", "") in k_clean.replace("-", "")
            ):
                return v

        # 3. Fallback to first connected provider if available
        connected = self.list_connected()
        if connected:
            logger.warning(f"Provider '{name}' not found in registry; falling back to connected provider '{connected[0].name}'")
            return connected[0]

        # 4. Fallback to first available provider
        if self._providers:
            first_p = list(self._providers.values())[0]
            logger.warning(f"Provider '{name}' not found in registry; falling back to '{first_p.name}'")
            return first_p

        available = ", ".join(list(self._providers.keys())[:10]) + "..."
        raise ProviderNotFoundError(f"Provider '{name}' not found. Available: {available}")

    def get_all(self) -> dict[str, ProviderDefinition]:
        """Get dict of all registered provider definitions."""
        return self._providers

    def list_providers(self) -> list[ProviderDefinition]:
        """Get all registered provider definitions."""
        return list(self._providers.values())

    def list_names(self) -> list[str]:
        """Get all registered provider names."""
        return list(self._providers.keys())

    def list_connected(self) -> list[ProviderDefinition]:
        """Get list of provider definitions that have connected API keys."""
        return [p for p in self._providers.values() if p.is_connected]

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        clean = name.strip().lower()
        return clean in self._providers or any(k.lower() == clean for k in self._providers)
