"""
Get contacts tool for Telegram User Account (MTProto).
Retrieves your saved personal Telegram contacts list.
"""

from telethon.tl.functions.contacts import GetContactsRequest

from ..client import get_telegram_client, run_async

NAME = "get_contacts"
DESCRIPTION = "Retrieve your saved Telegram personal contacts (names, usernames, phone numbers, user IDs)."


async def _get_user_contacts(limit: int = 50) -> str:
    """Async helper to get saved contacts via Telethon TL function."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        res = await client(GetContactsRequest(hash=0))
        await client.disconnect()

        users = getattr(res, "users", [])
        if not users:
            return "Telegram: No saved contacts found in your account."

        # Limit contacts display
        users_slice = users[:limit]
        output = [f"📇 Saved Telegram Contacts ({len(users_slice)} of {len(users)} total):\n"]

        for u in users_slice:
            first = getattr(u, "first_name", "") or ""
            last = getattr(u, "last_name", "") or ""
            full_name = f"{first} {last}".strip() or "Unnamed Contact"
            u_username = getattr(u, "username", None)
            username = f"@{u_username}" if u_username else "N/A"
            u_phone = getattr(u, "phone", None)
            phone = f"+{u_phone}" if u_phone else "Hidden"
            user_id = u.id

            output.append(f"  • {full_name} | Username: {username} | Phone: {phone} | User ID: {user_id}")

        return "\n".join(output)

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to retrieve Telegram contacts: {e}"


def get_contacts(limit: int = 50) -> str:
    """
    Retrieve your saved Telegram contacts.

    Args:
        limit: Maximum number of contacts to display (default: 50).

    Returns:
        Formatted summary of saved contacts.
    """
    try:
        return run_async(_get_user_contacts, limit)
    except Exception as e:
        return f"Error: {e}"
