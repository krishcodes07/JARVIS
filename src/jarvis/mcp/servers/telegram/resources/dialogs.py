"""
Telegram User Dialogs Resource.
Exposes telegram://dialogs
"""

from ..tools.list_dialogs import list_dialogs

URI = "telegram://dialogs"
NAME = "Telegram Account Dialogs"
DESCRIPTION = "Live summary of your recent personal Telegram chats, DMs, groups, and channels."
MIME_TYPE = "text/plain"


def dialogs() -> str:
    """Read personal Telegram dialogs as a contextual resource."""
    return list_dialogs(limit=25)
