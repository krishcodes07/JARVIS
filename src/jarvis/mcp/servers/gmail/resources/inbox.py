"""
Gmail Inbox Resource loader.
Exposes gmail://inbox
"""

from ..tools.read_emails import read_emails

URI = "gmail://inbox"
NAME = "Gmail Inbox"
DESCRIPTION = "Live summary of the most recent emails in your Gmail inbox."
MIME_TYPE = "text/plain"


def inbox() -> str:
    """Fetch and return the recent inbox content as a contextual resource."""
    return read_emails(folder="INBOX", count=5)
