"""
Token Store — Persistent credential and OAuth token management for JARVIS.

Stores OAuth access & refresh tokens at `~/.jarvis/auth/tokens.json`.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from jarvis.core.paths import get_jarvis_home

logger = logging.getLogger(__name__)


def get_tokens_file_path() -> Path:
    """Get the path to the persistent auth tokens file (~/.jarvis/auth/tokens.json)."""
    try:
        return get_jarvis_home() / "auth" / "tokens.json"
    except Exception:
        from jarvis.core.config import CONFIG_DIR
        return CONFIG_DIR / "tokens.json"


class TokenStore:
    """Manages persistent credentials and OAuth tokens."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_tokens_file_path()
        self._tokens: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Load stored tokens from disk."""
        if not self.path.exists():
            self._tokens = {}
            return

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._tokens = data.get("tokens", data)
            else:
                self._tokens = {}
        except Exception as e:
            logger.warning("Failed to load tokens from %s: %s", self.path, e)
            self._tokens = {}

    def save(self) -> None:
        """Persist tokens to disk."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"tokens": self._tokens}
            self.path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Saved %d provider tokens to %s", len(self._tokens), self.path)
        except Exception as e:
            logger.error("Failed to save tokens to %s: %s", self.path, e)

    def save_token(self, provider: str, data: dict[str, Any]) -> None:
        """Save or update tokens for a given provider (e.g. 'google', 'github').

        Args:
            provider: Identifier for the provider (lowercase).
            data: Token payload (access_token, refresh_token, expires_at, etc.).
        """
        provider_key = provider.strip().lower()
        # Compute expires_at timestamp if expires_in is provided
        if "expires_in" in data and "expires_at" not in data:
            try:
                data["expires_at"] = time.time() + float(data["expires_in"])
            except (ValueError, TypeError):
                pass

        if "saved_at" not in data:
            data["saved_at"] = time.time()

        self._tokens[provider_key] = data
        self.save()

    def get_token(self, provider: str) -> dict[str, Any] | None:
        """Retrieve token data for a provider."""
        self.load()
        return self._tokens.get(provider.strip().lower())

    def get_access_token(self, provider: str) -> str | None:
        """Retrieve the raw access token string for a provider."""
        token_data = self.get_token(provider)
        if not token_data:
            return None
        return token_data.get("access_token")

    def is_authenticated(self, provider: str) -> bool:
        """Check if valid credentials exist for a provider."""
        token_data = self.get_token(provider)
        if not token_data:
            return False
        return bool(token_data.get("access_token") or token_data.get("refresh_token"))

    def is_expired(self, provider: str, buffer_seconds: int = 60) -> bool:
        """Check if the access token for a provider has expired or is about to expire."""
        token_data = self.get_token(provider)
        if not token_data:
            return True
        expires_at = token_data.get("expires_at")
        if expires_at is None:
            # If no expiration timestamp is stored, assume not expired if access token exists
            return False
        try:
            return time.time() + buffer_seconds >= float(expires_at)
        except (ValueError, TypeError):
            return False

    def remove_token(self, provider: str) -> bool:
        """Remove stored credentials for a provider."""
        provider_key = provider.strip().lower()
        if provider_key in self._tokens:
            del self._tokens[provider_key]
            self.save()
            return True
        return False

    def list_authenticated_providers(self) -> list[str]:
        """List all providers with stored credentials."""
        self.load()
        return list(self._tokens.keys())


# Singleton instance for platform-wide access
token_store = TokenStore()
