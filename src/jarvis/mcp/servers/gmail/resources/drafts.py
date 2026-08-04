"""
Gmail Drafts Resource loader.
Exposes gmail://drafts
"""

from ..tools.read_emails import read_emails

URI = "gmail://drafts"
NAME = "Gmail Drafts"
DESCRIPTION = "Overview of current email drafts stored in Gmail."
MIME_TYPE = "text/plain"


def drafts() -> str:
    """Fetch and return draft emails content as a contextual resource."""
    return read_emails(folder="[Gmail]/Drafts", count=5)
