"""
Pin / unpin message tool for Telegram MCP Server (MTProto).
Allows pinning or unpinning messages in Telegram chats, groups, or channels.
"""

from ..client import get_telegram_client, run_async

NAME = "pin_message"
DESCRIPTION = "Pin or unpin a specific message in a Telegram chat, group, or channel."


async def _pin_user_message(
    chat_id: str, message_id: int, unpin: bool = False, notify: bool = False
) -> str:
    """Async helper to pin/unpin message via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        msg_id = int(message_id)

        if unpin:
            await client.unpin_message(target, msg_id)
            status_text = f"Unpinned message ID {msg_id}"
        else:
            await client.pin_message(target, msg_id, notify=notify)
            status_text = f"Pinned message ID {msg_id}"

        await client.disconnect()
        return f"[OK] {status_text} in chat '{chat_id}'."

    except Exception as e:
        await client.disconnect()
        action_name = "unpin" if unpin else "pin"
        return f"Error: Failed to {action_name} message {message_id} in '{chat_id}': {e}"


def pin_message(
    chat_id: str, message_id: int, unpin: bool = False, notify: bool = False
) -> str:
    """
    Pin or unpin a message in a Telegram chat.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_id: ID of the message to pin or unpin.
        unpin: Set to True to unpin the message, False to pin.
        notify: Whether to send a notification to chat members upon pinning (default: False).

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_pin_user_message, chat_id, message_id, unpin, notify)
    except Exception as e:
        return f"Error: {e}"
