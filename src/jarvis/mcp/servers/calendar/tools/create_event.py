"""
Create event tool for Calendar.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from ..config import load_events, save_events

NAME = "create_event"
DESCRIPTION = "Create a new calendar event with title, start/end times, optional description and location."


def _parse_dt(value: str) -> str:
    """Normalize an ISO-like datetime string; naive times default to UTC."""
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=None)
    return parsed.isoformat()


def create_event(
    title: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """
    Create a new calendar event.

    Args:
        title: Event title.
        start: Start time as ISO 8601 string (e.g. '2026-08-01T10:00:00').
        end: End time as ISO 8601 string (e.g. '2026-08-01T11:00:00').
        description: Optional event description.
        location: Optional event location.

    Returns:
        Confirmation message including the new event ID.
    """
    try:
        if not title.strip():
            return "Error: title is required."

        event = {
            "id": uuid.uuid4().hex[:12],
            "title": title.strip(),
            "start": _parse_dt(start),
            "end": _parse_dt(end),
            "description": description,
            "location": location,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        events = load_events()
        events.append(event)
        save_events(events)

        return (
            f"[OK] Created event '{title}' (ID: {event['id']}) "
            f"from {event['start']} to {event['end']}."
        )
    except Exception as e:
        return f"Error: Failed to create event: {e}"
