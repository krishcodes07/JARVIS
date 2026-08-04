"""
Calendar Upcoming Events Resource.
Exposes calendar://upcoming
"""

from ..tools.list_events import list_events

URI = "calendar://upcoming"
NAME = "Upcoming Calendar Events"
DESCRIPTION = "Live list of upcoming calendar events, sorted by start time."
MIME_TYPE = "text/plain"


def upcoming() -> str:
    """Return the next 10 upcoming events as a contextual resource."""
    return list_events(limit=10)
