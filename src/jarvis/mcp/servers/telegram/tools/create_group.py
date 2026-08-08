"""
Create group tool for Telegram MCP Server (MTProto).
Creates a new Telegram group chat with a title and specified users.
"""

from typing import Any

from telethon import functions, types, utils

from ..client import get_telegram_client, run_async

NAME = "create_group"
DESCRIPTION = "Create a new Telegram group chat with a title and invite specified users (@username, user ID, or phone)."


async def _create_user_group(title: str, users: str | list[str]) -> str:
    """Async helper to create a group chat via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        user_list = []
        if isinstance(users, str):
            user_list = [u.strip() for u in users.split(",") if u.strip()]
        elif isinstance(users, list):
            user_list = [str(u).strip() for u in users if str(u).strip()]

        if not user_list:
            await client.disconnect()
            return "Error: At least one user must be provided to create a group chat."

        input_users: list[types.TypeInputUser] = []
        for u in user_list:
            target = int(u) if (u.isdigit() or (u.startswith("-") and u[1:].isdigit())) else u
            entity = await client.get_input_entity(target)
            user_input = utils.get_input_user(entity)
            if user_input:
                input_users.append(user_input)

        if not input_users:
            await client.disconnect()
            return "Error: Could not resolve valid user inputs for creating group chat."

        result = await client(functions.messages.CreateChatRequest(users=input_users, title=title))
        await client.disconnect()

        chats = getattr(result, "chats", [])
        chat_obj: Any = chats[0] if (chats and isinstance(chats, list)) else None
        chat_id = getattr(chat_obj, "id", "unknown") if chat_obj else "unknown"
        return f"[OK] Successfully created group chat '{title}' (Chat ID: {chat_id}) with {len(input_users)} member(s)."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to create group chat '{title}': {e}"


def create_group(title: str, users: str) -> str:
    """
    Create a new Telegram group chat.

    Args:
        title: Title/name of the new group chat.
        users: Comma-separated usernames, phone numbers, or user IDs to include in the group.

    Returns:
        Status confirmation message with new group ID.
    """
    try:
        return run_async(_create_user_group, title, users)
    except Exception as e:
        return f"Error: {e}"
