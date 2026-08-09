"""
Cache Utility Module for JARVIS TUI.
Handles reading and writing persistent user state (recent models, model cache, pinned sessions).
"""

from __future__ import annotations

import json
import logging

from jarvis.core.paths import get_cache_dir

logger = logging.getLogger(__name__)

CACHE_DIR = get_cache_dir()
RECENT_MODELS_PATH = CACHE_DIR / "recent_models.json"
MODELS_CACHE_PATH = CACHE_DIR / "models_cache.json"
PINNED_SESSIONS_PATH = CACHE_DIR / "pinned_sessions.json"


def ensure_cache_dir() -> None:
    """Ensure the cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ─── Recent Models Cache ───

def load_recent_models() -> list[dict[str, str]]:
    """Load up to 5 recently used models from disk."""
    ensure_cache_dir()
    if RECENT_MODELS_PATH.exists():
        try:
            with open(RECENT_MODELS_PATH, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data[:5]
        except Exception as e:
            logger.warning("Failed to read recent_models.json: %s", e)
    return []


def save_recent_model(model_item: dict[str, str]) -> None:
    """Save a model item into the recently used models list (max 5)."""
    ensure_cache_dir()
    recents = load_recent_models()
    mid = model_item.get("id", "")
    if not mid:
        return
    recents = [m for m in recents if m.get("id") != mid]
    recents.insert(
        0,
        {
            "id": mid,
            "name": model_item.get("name", mid),
            "provider": model_item.get("provider", "").lower(),
        },
    )
    recents = recents[:5]
    try:
        with open(RECENT_MODELS_PATH, "w", encoding="utf-8") as f:
            json.dump(recents, f, indent=2)
    except Exception as e:
        logger.warning("Could not save recent model: %s", e)


# ─── Models Provider Cache ───

def load_models_cache() -> dict[str, list[dict[str, str]]]:
    """Load cached model lists per provider from disk."""
    ensure_cache_dir()
    if MODELS_CACHE_PATH.exists():
        try:
            with open(MODELS_CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning("Failed to read models_cache.json: %s", e)
    return {}


def save_models_cache(cache_data: dict[str, list[dict[str, str]]]) -> None:
    """Save model lists per provider to disk."""
    ensure_cache_dir()
    try:
        with open(MODELS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.warning("Could not save models cache: %s", e)


# ─── Pinned Sessions Cache ───

def load_pinned_sessions() -> set[str]:
    """Load set of pinned session IDs from disk."""
    ensure_cache_dir()
    if PINNED_SESSIONS_PATH.exists():
        try:
            with open(PINNED_SESSIONS_PATH, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.warning("Failed to read pinned_sessions.json: %s", e)
    return set()


def save_pinned_sessions(pinned: set[str]) -> None:
    """Save set of pinned session IDs to disk."""
    ensure_cache_dir()
    try:
        with open(PINNED_SESSIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(list(pinned), f, indent=2)
    except Exception as e:
        logger.warning("Could not save pinned_sessions.json: %s", e)
