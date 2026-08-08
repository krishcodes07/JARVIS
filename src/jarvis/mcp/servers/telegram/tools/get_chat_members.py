"""
Get chat members tool for Telegram MCP Server (MTProto).
Retrieves the list of participants/members in a Telegram group or channel.
"""

from ..client import get_telegram_client, run_async

NAME = "get_chat_members"
DESCRIPTION = (
    "Get the list of participants/members in a Telegram group or channel, including ID, name, "
    "username, and bot status."
)


async def _get_user_chat_members(chat_id: str, limit: int = 50) -> str:
    """Async helper to retrieve chat participants via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        participants = await client.get_participants(target, limit=limit)
        await client.disconnect()

        if not participants:
            return f"No participants found or access restricted for chat '{chat_id}'."

        results = []
        for p in participants:
            name = f"{p.first_name or ''} {p.last_name or ''}".strip() or "Unknown Name"
            p_username = getattr(p, "username", None)
            username = f"@{p_username}" if p_username else "No username"
            bot_tag = " [BOT]" if getattr(p, "bot", False) else ""
            results.append(f"- ID: {p.id} | {name} ({username}){bot_tag}")

        return f"Found {len(results)} member(s) in '{chat_id}':\n" + "\n".join(results)

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to get chat members for '{chat_id}': {e}"


def get_chat_members(chat_id: str, limit: int = 50) -> str:
    """
    Get participants in a Telegram group or channel.

    Args:
        chat_id: Telegram group/channel ID or @username.
        limit: Maximum number of members to retrieve (default: 50).

    Returns:
        Formatted member listing or error message.
    """
    try:
        return run_async(_get_user_chat_members, chat_id, limit)
    except Exception as e:
        return f"Error: {e}"
