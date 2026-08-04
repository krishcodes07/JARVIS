"""
Get account info tool for Telegram User Account (MTProto).
"""

from ..client import get_telegram_client, run_async

NAME = "get_account_info"
DESCRIPTION = "Retrieve your personal Telegram account details (Username, Phone Number, Account ID, Profile Status)."


async def _get_user_info() -> str:
    """Async helper to get account info via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        me = await client.get_me()
        await client.disconnect()

        return (
            f"👤 Your Personal Telegram Account Info:\n"
            f"  • Display Name: {me.first_name} {me.last_name or ''}\n"
            f"  • Username: @{me.username or 'N/A'}\n"
            f"  • Phone Number: +{me.phone or 'Hidden'}\n"
            f"  • Account ID: {me.id}\n"
            f"  • Status: Active & Authorized"
        )
    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to get Telegram account info: {e}"


def get_account_info() -> str:
    """
    Get personal Telegram account details.

    Returns:
        Summary of user account profile.
    """
    try:
        return run_async(_get_user_info)
    except Exception as e:
        return f"Error: {e}"
