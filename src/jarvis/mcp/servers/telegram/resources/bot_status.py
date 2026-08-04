"""
Telegram Bot Status Resource.
Exposes telegram://bot_status
"""

from ..tools.get_bot_info import get_bot_info

URI = "telegram://bot_status"
NAME = "Telegram Bot Status"
DESCRIPTION = "Live status, profile details, and info for the connected Telegram bot."
MIME_TYPE = "text/plain"


def bot_status() -> str:
    """Read Telegram bot status as a contextual resource."""
    return get_bot_info()
