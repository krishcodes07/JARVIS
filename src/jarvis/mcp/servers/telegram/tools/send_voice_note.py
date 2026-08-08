"""
Send voice note tool for Telegram MCP Server (MTProto).
Sends an audio file as a playable Telegram voice note.
"""

from typing import Any

from ..client import get_telegram_client, run_async

NAME = "send_voice_note"
DESCRIPTION = (
    "Send an audio file (OGG/OPUS, MP3, WAV) formatted as a native playable Telegram voice note "
    "to a chat or user."
)


async def _send_user_voice_note(
    chat_id: str,
    file_path: str,
    caption: str | None = None,
    reply_to_id: int | None = None,
) -> str:
    """Async helper to send a voice note via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id

        caption_val: Any = caption or None
        reply_to_val: Any = reply_to_id
        sent_msg = await client.send_file(
            target,
            file_path,
            voice_note=True,
            caption=caption_val,
            reply_to=reply_to_val,
        )
        await client.disconnect()
        msg_obj: Any = sent_msg[0] if isinstance(sent_msg, list) else sent_msg
        msg_id = getattr(msg_obj, "id", "unknown")
        return f"[OK] Voice note '{file_path}' sent to '{chat_id}' (Message ID: {msg_id})."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to send voice note to '{chat_id}': {e}"


def send_voice_note(
    chat_id: str,
    file_path: str,
    caption: str | None = None,
    reply_to_id: int | None = None,
) -> str:
    """
    Send a voice note from your personal Telegram account.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        file_path: Path to the audio file to send as a voice note.
        caption: Optional text caption.
        reply_to_id: Optional message ID to reply to.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_send_user_voice_note, chat_id, file_path, caption, reply_to_id)
    except Exception as e:
        return f"Error: {e}"
