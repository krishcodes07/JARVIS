"""
Configuration and storage helpers for Calendar MCP server.
Events are persisted in a single JSON file (no external service required).
"""

from __future__ import annotations

import json
import os
from typing import Any

STORE_PATH = os.environ.get("CALENDAR_STORE_PATH", "").strip() or "data/mcp_calendar.json"


def get_store_path() -> str:
    """Return the resolved calendar store path."""
    expanded = os.path.expanduser(STORE_PATH)
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(os.getcwd(), expanded)


def load_events() -> list[dict[str, Any]]:
    """Load all events from the store file."""
    path = get_store_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_events(events: list[dict[str, Any]]) -> None:
    """Persist all events to the store file."""
    path = get_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def validate() -> list[str]:
    """Validate calendar configuration."""
    return []
