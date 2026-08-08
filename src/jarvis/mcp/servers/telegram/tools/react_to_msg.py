"""
React to message tool for Telegram MCP Server (MTProto).
Sends an emoji reaction (e.g. 👍, ❤️, 🔥, 😂, 🎉) to a specific message in a chat.
"""

from telethon import functions, types

from ..client import get_telegram_client, run_async

NAME = "react_to_msg"
DESCRIPTION = (
    "Send an emoji reaction (e.g. '👍', '❤️', '🔥', '😂', '🎉', '👏', '👎') to a Telegram message. "
    "Pass an empty reaction string to clear existing reactions."
)


async def _react_to_user_message(chat_id: str, message_id: int, reaction: str = "👍") -> str:
    """Async helper to send a reaction via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        peer = await client.get_input_entity(target)
        msg_id = int(message_id)

        reaction_str = (reaction or "").strip()
        reactions: list[types.TypeReaction] = [types.ReactionEmoji(emoticon=reaction_str)] if reaction_str else []

        await client(
            functions.messages.SendReactionRequest(
                peer=peer,
                msg_id=msg_id,
                reaction=reactions,
            )
        )
        await client.disconnect()

        action = f"Reacted '{reaction_str}' to" if reaction_str else "Removed reaction from"
        return f"[OK] {action} message ID {msg_id} in '{chat_id}'."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to react to message {message_id} in '{chat_id}': {e}"


def react_to_msg(chat_id: str, message_id: int, reaction: str = "👍") -> str:
    """
    Add or remove an emoji reaction on a Telegram message.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_id: ID of the message to react to.
        reaction: Emoji string (e.g. '👍', '❤️', '🔥') or empty string '' to remove reactions.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_react_to_user_message, chat_id, message_id, reaction)
    except Exception as e:
        return f"Error: {e}"
