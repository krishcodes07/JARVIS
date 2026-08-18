"""
models.dev Integration — Loads, caches, and manages LLM provider metadata from models.dev database.

Fetches 180+ providers and their model catalogs from https://models.dev/api.json and caches
them locally in ~/.jarvis/workspace/cache/models_dev_cache.json.
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

MODELS_DEV_CACHE_FILE = DATA_DIR / "cache" / "models_dev_cache.json"
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
    from jarvis.core.config import PROJECT_ROOT

    if MODELS_DEV_CACHE_FILE.exists():
        try:
            with open(MODELS_DEV_CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception as e:
            logger.warning(f"Failed loading models.dev cache from {MODELS_DEV_CACHE_FILE}: {e}")

    # Check legacy user workspace location (~/.jarvis/workspace/models_dev_cache.json)
    legacy_user_cache = DATA_DIR / "models_dev_cache.json"
    if legacy_user_cache.exists():
        try:
            with open(legacy_user_cache, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    save_models_dev_cache(data)
                    return data
        except Exception as e:
            logger.warning(f"Failed loading legacy models.dev cache from {legacy_user_cache}: {e}")

    # Fallback to repo data catalog file
    repo_cache = PROJECT_ROOT / "data" / "models_dev_cache.json"
    if repo_cache.exists():
        try:
            with open(repo_cache, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    save_models_dev_cache(data)
                    return data
        except Exception as e:
            logger.warning(f"Failed loading fallback models.dev cache from {repo_cache}: {e}")

    return {}


def save_models_dev_cache(data: dict[str, Any]) -> None:
    """Save models.dev data to local cache file in ~/.jarvis/workspace/cache/models_dev_cache.json."""
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
    envs = get_provider_env_vars(provider_id, provider_data)
    return envs[0]


def get_provider_env_vars(
    provider_id: str,
    provider_data: dict[str, Any] | None = None,
    filter_synonyms: bool = True,
) -> list[str]:
    """Determine all environment variable names required for a provider.

    For example, Cloudflare requires ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_KEY"].
    If *filter_synonyms* is True, multiple alternative API keys (e.g.
    GOOGLE_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY, GEMINI_API_KEY) are deduplicated
    so the user is only prompted for the 1st one.
    """
    if provider_data is None:
        cache = load_models_dev_cache()
        provider_data = cache.get(provider_id, {})

    raw_envs: list[str] = []
    if provider_data and isinstance(provider_data.get("env"), list):
        raw_envs = [str(e).strip() for e in provider_data["env"] if str(e).strip()]

    if not raw_envs:
        clean_id = provider_id.upper().replace("-", "_").replace(".", "_")
        raw_envs = [f"{clean_id}_API_KEY"]

    if not filter_synonyms:
        return raw_envs

    # Filter out duplicate API_KEY synonyms (keep only the 1st env containing "API_KEY")
    result: list[str] = []
    seen_api_key = False
    for env in raw_envs:
        if "API_KEY" in env.upper():
            if not seen_api_key:
                result.append(env)
                seen_api_key = True
        else:
            result.append(env)

    return result


def format_env_var_label(env_var: str) -> str:
    """Format an environment variable name into a clean, human-readable title by splitting by '_' and capitalizing each word.

    Examples:
        CLOUDFLARE_ACCOUNT_ID -> Cloudflare Account Id
        CLOUDFLARE_API_KEY -> Cloudflare Api Key
    """
    if not env_var:
        return ""
    return " ".join(part.capitalize() for part in env_var.split("_") if part)


def is_provider_connected(provider_id: str, provider_data: dict[str, Any] | None = None) -> bool:
    """Check whether all required API keys/env vars for the provider are set and non-empty in os.environ or .env."""
    from dotenv import load_dotenv
    from jarvis.core.config import PROJECT_ROOT, get_jarvis_home

    repo_env = PROJECT_ROOT / ".env"
    home_env = get_jarvis_home() / ".env"

    if repo_env.exists():
        load_dotenv(repo_env)
    if home_env.exists():
        load_dotenv(home_env, override=True)

    if provider_data is None:
        cache = load_models_dev_cache()
        provider_data = cache.get(provider_id, {})

    raw_envs = get_provider_env_vars(provider_id, provider_data, filter_synonyms=False)

    api_key_group = [e for e in raw_envs if "API_KEY" in e.upper()]
    non_api_key_group = [e for e in raw_envs if "API_KEY" not in e.upper()]

    # 1. Non-API-KEY required env vars (e.g. CLOUDFLARE_ACCOUNT_ID): ALL must be set
    for env_var in non_api_key_group:
        val = os.getenv(env_var, "").strip()
        if not val:
            return False

    # 2. API-KEY env vars (e.g. GOOGLE_API_KEY / GEMINI_API_KEY): At least ONE must be set
    if api_key_group:
        has_any_key = False
        for env_var in api_key_group:
            val = os.getenv(env_var, "").strip()
            if val and not val.startswith("sk-..."):
                has_any_key = True
                break
        if not has_any_key:
            return False

    return True


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


def get_model_context_limit(model_id: str, provider_id: str | None = None) -> int:
    """Get context window limit for a model from models.dev cache.

    Default fallback: 128,000 tokens if limit is not found in cache.
    """
    if not model_id:
        return 128000

    cache = load_models_dev_cache()
    if not cache:
        return 128000

    clean_model_id = model_id
    if "/" in model_id:
        parts = model_id.split("/", 1)
        if not provider_id:
            provider_id = parts[0]
        clean_model_id = parts[1]

    # 1. Direct lookup under provider_id if given
    if provider_id:
        prov_clean = provider_id.lower()
        for p_id, p_data in cache.items():
            if p_id.lower() == prov_clean:
                models = p_data.get("models", {})
                for m_key, m_data in models.items():
                    if m_key.lower() in (model_id.lower(), clean_model_id.lower()):
                        ctx = m_data.get("limit", {}).get("context")
                        if isinstance(ctx, (int, float)) and ctx > 0:
                            return int(ctx)

    # 2. Search across all providers in cache
    for p_data in cache.values():
        models = p_data.get("models", {})
        for m_key, m_data in models.items():
            if m_key.lower() in (model_id.lower(), clean_model_id.lower()):
                ctx = m_data.get("limit", {}).get("context")
                if isinstance(ctx, (int, float)) and ctx > 0:
                    return int(ctx)

    return 128000

