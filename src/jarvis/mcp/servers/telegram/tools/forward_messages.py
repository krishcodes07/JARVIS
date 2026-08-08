"""
Forward messages tool for Telegram MCP Server (MTProto).
Forwards one or multiple messages from a source chat to a destination chat.
"""

from ..client import get_telegram_client, run_async

NAME = "forward_messages"
DESCRIPTION = (
    "Forward one or multiple messages from a source Telegram chat to a destination chat. "
    "Accepts a single message ID or a comma-separated list of message IDs."
)


async def _forward_user_messages(
    from_chat_id: str, to_chat_id: str, message_ids: int | str | list[int]
) -> str:
    """Async helper to forward messages via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        from_target = (
            int(from_chat_id)
            if (from_chat_id.isdigit() or (from_chat_id.startswith("-") and from_chat_id[1:].isdigit()))
            else from_chat_id
        )
        to_target = (
            int(to_chat_id)
            if (to_chat_id.isdigit() or (to_chat_id.startswith("-") and to_chat_id[1:].isdigit()))
            else to_chat_id
        )

        ids_to_forward = []
        if isinstance(message_ids, int):
            ids_to_forward = [message_ids]
        elif isinstance(message_ids, str):
            ids_to_forward = [int(mid.strip()) for mid in message_ids.split(",") if mid.strip().isdigit()]
        elif isinstance(message_ids, list):
            ids_to_forward = [int(mid) for mid in message_ids]

        if not ids_to_forward:
            await client.disconnect()
            return "Error: No valid message IDs provided to forward."

        forwarded = await client.forward_messages(to_target, ids_to_forward, from_target)
        await client.disconnect()

        fwd_count = len(forwarded) if isinstance(forwarded, list) else 1
        return (
            f"[OK] Successfully forwarded {fwd_count} message(s) "
            f"(IDs: {ids_to_forward}) from '{from_chat_id}' to '{to_chat_id}'."
        )

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to forward message(s) from '{from_chat_id}' to '{to_chat_id}': {e}"


def forward_messages(
    from_chat_id: str, to_chat_id: str, message_ids: int | str
) -> str:
    """
    Forward messages between Telegram chats.

    Args:
        from_chat_id: Source chat ID, @username, or phone number.
        to_chat_id: Destination chat ID, @username, or phone number.
        message_ids: Single message ID (int) or comma-separated list of IDs (e.g. '100' or '100,101').

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_forward_user_messages, from_chat_id, to_chat_id, message_ids)
    except Exception as e:
        return f"Error: {e}"
