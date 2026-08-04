"""
List dialogs tool for Telegram User Account (MTProto).
Lists recent personal chats, DMs, groups, and channels with optional filtering by type.
"""

from typing import Optional
from ..client import get_telegram_client, run_async

NAME = "list_dialogs"
DESCRIPTION = (
    "List your recent personal Telegram chats, direct messages, groups, and channels with chat IDs. "
    "Supports filtering by type ('all', 'users' / 'dms', 'groups', 'channels')."
)


async def _list_user_dialogs(limit: int = 20, filter_type: str = "all") -> str:
    """Async helper to list dialogs via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        dialogs = await client.get_dialogs(limit=100 if filter_type != "all" else limit)
        await client.disconnect()

        if not dialogs:
            return "Telegram: No active dialogs found."

        ft = (filter_type or "all").lower().strip()
        filtered = []
        for d in dialogs:
            if ft in ("users", "user", "dms", "dm") and not d.is_user:
                continue
            if ft in ("groups", "group") and not d.is_group:
                continue
            if ft in ("channels", "channel") and not d.is_channel:
                continue
            filtered.append(d)

        filtered = filtered[:limit]
        if not filtered:
            return f"Telegram: No chats matching filter '{filter_type}' found."

        output = [f"💬 Your Recent Telegram Chat(s) [Filter: '{filter_type}'] ({len(filtered)} total):\n"]
        for d in filtered:
            title = d.name or "Unnamed Chat"
            chat_id = d.id
            unread = f" ({d.unread_count} unread)" if d.unread_count else ""
            entity_type = "User/DM" if d.is_user else ("Group" if d.is_group else "Channel")

            output.append(f"  • {title} | Type: {entity_type} | Chat ID: {chat_id}{unread}")

        return "\n".join(output)

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to list Telegram dialogs: {e}"


def list_dialogs(limit: int = 20, filter_type: str = "all") -> str:
    """
    List recent personal Telegram chats.

    Args:
        limit: Maximum number of recent chats to return (default: 20).
        filter_type: Filter by chat type: 'all', 'users' (or 'dms'), 'groups', 'channels' (default: 'all').

    Returns:
        Formatted list of chats with titles and chat IDs.
    """
    try:
        return run_async(_list_user_dialogs, limit, filter_type)
    except Exception as e:
        return f"Error: {e}"
