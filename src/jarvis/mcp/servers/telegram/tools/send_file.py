"""
Send file tool for Telegram MCP Server (MTProto).
Uploads and sends any document, photo, video, audio, or file to a Telegram chat.
"""

from typing import Any

from ..client import get_telegram_client, run_async

NAME = "send_file"
DESCRIPTION = (
    "Send a file (document, video, audio, archive, or image) to a Telegram chat or user. "
    "Supports local file paths or public file URLs, optional captions, and message replies."
)


async def _send_user_file(
    chat_id: str,
    file_path: str,
    caption: str | None = None,
    reply_to_id: int | None = None,
    force_document: bool = False,
) -> str:
    """Async helper to send a file via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return (
            "Error: Telegram user session is not authorized. "
            "Please run 'python -m jarvis.mcp.servers.telegram.login' to log into your Telegram account once."
        )

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id

        caption_val: Any = caption or None
        reply_to_val: Any = reply_to_id
        sent_msg = await client.send_file(
            target,
            file_path,
            caption=caption_val,
            reply_to=reply_to_val,
            force_document=force_document,
        )
        await client.disconnect()
        msg_obj: Any = sent_msg[0] if isinstance(sent_msg, list) else sent_msg
        msg_id = getattr(msg_obj, "id", "unknown")
        return f"[OK] File '{file_path}' sent to '{chat_id}' (Message ID: {msg_id})."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to send file to '{chat_id}': {e}"


def send_file(
    chat_id: str,
    file_path: str,
    caption: str | None = None,
    reply_to_id: int | None = None,
    force_document: bool = False,
) -> str:
    """
    Send a file from your personal Telegram account.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        file_path: Absolute or relative local file path or public media URL.
        caption: Optional text caption accompanying the file.
        reply_to_id: Optional message ID to reply to.
        force_document: If True, sends photos/videos as uncompressed documents.

    Returns:
        Status confirmation message.
    """
    try:
        return run_async(_send_user_file, chat_id, file_path, caption, reply_to_id, force_document)
    except Exception as e:
        return f"Error: {e}"
