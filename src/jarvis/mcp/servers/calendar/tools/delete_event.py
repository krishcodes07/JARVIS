"""
Delete event tool for Calendar.
"""

from __future__ import annotations

from ..config import load_events, save_events

NAME = "delete_event"
DESCRIPTION = "Delete a calendar event by its event ID."


def delete_event(event_id: str) -> str:
    """
    Delete a calendar event by ID.

    Args:
        event_id: The event ID (returned when the event was created or listed).

    Returns:
        Confirmation or error message.
    """
    try:
        events = load_events()
        remaining = [e for e in events if e.get("id") != event_id]

        if len(remaining) == len(events):
            return f"Error: No event found with ID '{event_id}'."

        save_events(remaining)
        return f"[OK] Deleted event with ID '{event_id}'."
    except Exception as e:  # noqa: BLE001
        return f"Error: Failed to delete event: {e}"
