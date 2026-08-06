"""
Send message tool for Telegram User Account (MTProto).
Sends messages directly from your personal Telegram user account.
"""


from ..client import get_telegram_client, run_async

NAME = "send_message"
DESCRIPTION = (
    "Send a Telegram message directly from your personal Telegram account to any user, @username, "
    "phone number, or group/channel."
)


async def _send_user_message(recipient: str, text: str, reply_to_id: int | None = None) -> str:
    """Async helper to send message via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return (
            "Error: Telegram user session is not authorized. "
            "Please run 'python -m jarvis.mcp.servers.telegram.login' to log into your Telegram account once."
        )

    try:
        # Convert numeric ID strings if applicable
        target = int(recipient) if (recipient.isdigit() or (recipient.startswith("-") and recipient[1:].isdigit())) else recipient

        sent_msg = await client.send_message(target, text, reply_to=reply_to_id)
        await client.disconnect()
        return f"[OK] Message sent from your Telegram account to '{recipient}' (Message ID: {sent_msg.id})."
    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to send Telegram message to '{recipient}': {e}"


def send_message(recipient: str, text: str, reply_to_id: int | None = None) -> str:
    """
    Send a message from your personal Telegram account.

    Args:
        recipient: Telegram username (e.g. '@john'), phone number ('+123456789'), or chat ID.
        text: Text message content to send.
        reply_to_id: Optional message ID to reply to.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_send_user_message, recipient, text, reply_to_id)
    except Exception as e:
        return f"Error: {e}"

