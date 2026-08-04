"""
Read messages tool for Telegram User Account (MTProto).
Reads recent messages from any personal chat, channel, or group.
"""

from typing import Optional
from ..client import get_telegram_client, run_async

NAME = "read_messages"
DESCRIPTION = "Read recent messages from any personal Telegram chat, user (@username), or channel."


async def _read_user_messages(chat: str, limit: int = 10) -> str:
    """Async helper to read messages from a chat via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat) if (chat.isdigit() or (chat.startswith("-") and chat[1:].isdigit())) else chat
        messages = await client.get_messages(target, limit=limit)
        await client.disconnect()

        if not messages:
            return f"Telegram: No messages found in '{chat}'."

        output = [f"📩 Recent {len(messages)} Message(s) from '{chat}':\n"]
        for m in reversed(messages):
            sender = await m.get_sender() if hasattr(m, "get_sender") else None
            sender_name = getattr(sender, "first_name", getattr(sender, "username", "Unknown")) if sender else "System"
            text = m.text or "[Non-text message / Media]"

            date_str = m.date.strftime("%Y-%m-%d %H:%M:%S") if m.date else ""
            output.append(f"  • [{date_str}] {sender_name} (ID: {m.id}): {text}")

        return "\n".join(output)

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to read messages from '{chat}': {e}"


def read_messages(chat: str, limit: int = 10) -> str:
    """
    Read recent messages from a Telegram chat.

    Args:
        chat: Telegram username (e.g. '@john'), chat ID, or phone number.
        limit: Number of recent messages to retrieve (default: 10).

    Returns:
        Formatted message history.
    """
    try:
        return run_async(_read_user_messages, chat, limit)
    except Exception as e:
        return f"Error: {e}"
