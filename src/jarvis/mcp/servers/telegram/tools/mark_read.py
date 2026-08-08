"""
Mark read tool for Telegram MCP Server (MTProto).
Marks unread messages as read in a Telegram chat up to a specific message ID.
"""

from ..client import get_telegram_client, run_async

NAME = "mark_read"
DESCRIPTION = "Mark messages as read/seen in a Telegram chat up to a specific message ID (or latest)."


async def _mark_user_read(chat_id: str, max_id: int | None = None) -> str:
    """Async helper to send read acknowledgement via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        if max_id is not None:
            await client.send_read_acknowledge(target, max_id=max_id)
        else:
            await client.send_read_acknowledge(target)
        await client.disconnect()

        up_to = f" up to message ID {max_id}" if max_id else ""
        return f"[OK] Marked messages as read in chat '{chat_id}'{up_to}."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to mark messages as read in '{chat_id}': {e}"


def mark_read(chat_id: str, max_id: int | None = None) -> str:
    """
    Mark messages as read in a Telegram chat.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        max_id: Optional maximum message ID to acknowledge up to.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_mark_user_read, chat_id, max_id)
    except Exception as e:
        return f"Error: {e}"
