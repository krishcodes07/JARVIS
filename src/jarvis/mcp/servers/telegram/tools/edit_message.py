"""
Edit message tool for Telegram User Account (MTProto).
Allows editing the text content of a previously sent message in a chat.
"""

from ..client import get_telegram_client, run_async

NAME = "edit_message"
DESCRIPTION = "Edit the text content of a previously sent Telegram message in a chat using its message ID."


async def _edit_user_message(chat_id: str, message_id: int, new_text: str) -> str:
    """Async helper to edit message via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        msg_id = int(message_id)

        edited_msg = await client.edit_message(target, msg_id, new_text)
        await client.disconnect()
        if edited_msg:
            return f"[OK] Message ID {msg_id} in '{chat_id}' updated successfully to: '{new_text}'"
        return f"Error: Message ID {msg_id} could not be edited."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to edit message {message_id} in '{chat_id}': {e}"


def edit_message(chat_id: str, message_id: int, new_text: str) -> str:
    """
    Edit a previously sent message in a Telegram chat.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_id: ID of the message to edit.
        new_text: New text content for the message.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_edit_user_message, chat_id, message_id, new_text)
    except Exception as e:
        return f"Error: {e}"
