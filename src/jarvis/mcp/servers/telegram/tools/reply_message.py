"""
Reply to message tool for Telegram User Account (MTProto).
Allows replying directly to a specific message in a chat by message ID.
"""

from typing import Any

from ..client import get_telegram_client, run_async

NAME = "reply_message"
DESCRIPTION = "Reply directly to a specific message in a Telegram chat using its message ID."


async def _reply_to_user_message(chat_id: str, message_id: int, text: str) -> str:
    """Async helper to reply to a message via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        msg_id = int(message_id)

        sent_msg = await client.send_message(target, text, reply_to=msg_id)
        await client.disconnect()
        msg_obj: Any = sent_msg[0] if isinstance(sent_msg, list) else sent_msg
        new_msg_id = getattr(msg_obj, "id", "unknown")
        return f"[OK] Replied to message ID {msg_id} in '{chat_id}' (New Message ID: {new_msg_id})."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to reply to message {message_id} in '{chat_id}': {e}"


def reply_message(chat_id: str, message_id: int, text: str) -> str:
    """
    Reply to a specific message in a Telegram chat.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_id: Target message ID to reply to.
        text: Reply message text.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_reply_to_user_message, chat_id, message_id, text)
    except Exception as e:
        return f"Error: {e}"
