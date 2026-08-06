"""
List events tool for Calendar.
"""

from __future__ import annotations

from ..config import load_events

NAME = "list_events"
DESCRIPTION = "List calendar events, optionally filtered to a time range. Sorted by start time."


def _sort_key(event: dict) -> str:
    return str(event.get("start", ""))


def list_events(
    start: str | None = None,
    end: str | None = None,
    limit: int = 20,
) -> str:
    """
    List calendar events within an optional time range.

    Args:
        start: Optional start boundary (ISO 8601). Events starting after this are included.
        end: Optional end boundary (ISO 8601). Events starting before this are included.
        limit: Maximum number of events to return (default: 20).

    Returns:
        Formatted list of events with title, time, location, and ID.
    """
    try:
        events = load_events()
        events = sorted(events, key=_sort_key)

        if start:
            events = [e for e in events if str(e.get("start", "")) >= start]
        if end:
            events = [e for e in events if str(e.get("start", "")) <= end]

        events = events[: max(1, int(limit))]

        if not events:
            return "📅 No events found."

        lines = [f"Found {len(events)} event(s):\n"]
        for e in events:
            loc = f" @ {e['location']}" if e.get("location") else ""
            lines.append(
                f"• [{e['start']} → {e['end']}] {e['title']}{loc} (ID: {e['id']})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: Failed to list events: {e}"
