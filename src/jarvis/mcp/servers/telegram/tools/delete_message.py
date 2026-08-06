"""
Delete message tool for Telegram User Account (MTProto).
Allows deleting one or multiple messages in a chat by message ID(s).
"""


from ..client import get_telegram_client, run_async

NAME = "delete_message"
DESCRIPTION = (
    "Delete one or multiple messages from a Telegram chat by message ID(s). "
    "Accepts a single message ID or a comma-separated list of message IDs."
)


async def _delete_user_message(chat_id: str, message_ids: int | str | list[int], revoke: bool = True) -> str:
    """Async helper to delete message(s) via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        # Convert numeric ID strings if applicable
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id

        # Parse message IDs
        ids_to_delete = []
        if isinstance(message_ids, int):
            ids_to_delete = [message_ids]
        elif isinstance(message_ids, str):
            ids_to_delete = [int(mid.strip()) for mid in message_ids.split(",") if mid.strip().isdigit()]
        elif isinstance(message_ids, list):
            ids_to_delete = [int(mid) for mid in message_ids]

        if not ids_to_delete:
            await client.disconnect()
            return "Error: No valid message IDs provided to delete."

        await client.delete_messages(target, ids_to_delete, revoke=revoke)
        await client.disconnect()
        return f"[OK] Successfully deleted message ID(s): {ids_to_delete} from chat '{chat_id}'."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to delete message(s) from '{chat_id}': {e}"


def delete_message(chat_id: str, message_ids: int | str, revoke: bool = True) -> str:
    """
    Delete message(s) from a Telegram chat.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_ids: Single message ID (int) or comma-separated string of IDs (e.g. '123' or '123,124').
        revoke: Whether to delete for everyone in the chat (default: True).

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_delete_user_message, chat_id, message_ids, revoke)
    except Exception as e:
        return f"Error: {e}"
