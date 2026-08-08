"""
models.dev Integration — Loads, caches, and manages LLM provider metadata from models.dev database.

Fetches 180+ providers and their model catalogs from https://models.dev/api.json and caches
them locally in data/models_dev_cache.json.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from jarvis.core.config import DATA_DIR
from jarvis.core.constants import Protocol

logger = logging.getLogger(__name__)

MODELS_DEV_CACHE_FILE = DATA_DIR / "models_dev_cache.json"
MODELS_DEV_URL = "https://models.dev/api.json"

# Known default base URLs for standard providers when api field is null in models.dev
STANDARD_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "xai": "https://api.x.ai/v1",
    "togetherai": "https://api.together.xyz/v1",
    "cohere": "https://api.cohere.com/v2",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "opencode": "https://opencode.ai/zen/v1",
    "opencode-zen": "https://opencode.ai/zen/v1",
    "tokenrouter": "https://api.tokenrouter.com/v1",
}


def load_models_dev_cache() -> dict[str, Any]:
    """Load models.dev catalog from local cache file if available."""
    if MODELS_DEV_CACHE_FILE.exists():
        try:
            with open(MODELS_DEV_CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception as e:
            logger.warning(f"Failed loading models.dev cache: {e}")
    return {}


def save_models_dev_cache(data: dict[str, Any]) -> None:
    """Save models.dev data to local cache file."""
    try:
        MODELS_DEV_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MODELS_DEV_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved models.dev catalog ({len(data)} providers) to {MODELS_DEV_CACHE_FILE}")
    except Exception as e:
        logger.warning(f"Failed to save models.dev cache: {e}")


async def fetch_models_dev_data() -> dict[str, Any]:
    """Fetch live catalog from https://models.dev/api.json and update local cache."""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "JARVIS-AI-Assistant/1.0"},
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get(MODELS_DEV_URL)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data:
                save_models_dev_cache(data)
                return data
    except Exception as e:
        logger.warning(f"Could not fetch models.dev catalog online ({e}); using cache.")

    return load_models_dev_cache()


def get_provider_env_var(provider_id: str, provider_data: dict[str, Any]) -> str:
    """Determine primary environment variable name for a provider."""
    envs = provider_data.get("env")
    if envs and isinstance(envs, list) and len(envs) > 0:
        return str(envs[0]).strip()

    clean_id = provider_id.upper().replace("-", "_").replace(".", "_")
    return f"{clean_id}_API_KEY"


def is_provider_connected(provider_id: str, provider_data: dict[str, Any] | None = None) -> bool:
    """Check whether an API key for the provider is set and non-empty in os.environ or .env."""
    from dotenv import load_dotenv
    from jarvis.core.config import PROJECT_ROOT

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    if provider_data is None:
        cache = load_models_dev_cache()
        provider_data = cache.get(provider_id, {})

    envs: list[str] = []
    if provider_data and isinstance(provider_data.get("env"), list):
        envs = [str(e).strip() for e in provider_data["env"]]

    if not envs:
        clean_id = provider_id.upper().replace("-", "_").replace(".", "_")
        envs = [f"{clean_id}_API_KEY"]

    for env_var in envs:
        val = os.getenv(env_var, "").strip()
        if val and not val.startswith("sk-..."):
            return True

    return False


def get_provider_base_url(provider_id: str, provider_data: dict[str, Any]) -> str:
    """Determine base URL for a provider."""
    api_url = provider_data.get("api")
    if api_url and isinstance(api_url, str) and api_url.startswith("http"):
        return api_url.rstrip("/")

    clean_id = provider_id.lower()
    if clean_id in STANDARD_BASE_URLS:
        return STANDARD_BASE_URLS[clean_id]

    return f"https://api.{clean_id}.ai/v1"


def get_provider_protocol(provider_id: str, provider_data: dict[str, Any]) -> Protocol:
    """Determine LLM protocol for a provider."""
    clean_id = provider_id.lower()
    if "anthropic" in clean_id:
        return Protocol.ANTHROPIC
    if clean_id in ("google", "google-vertex", "gemini"):
        return Protocol.GOOGLE
    return Protocol.OPENAI
