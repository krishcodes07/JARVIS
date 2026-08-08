"""
Download media tool for Telegram MCP Server (MTProto).
Downloads media (photo, document, audio, video, voice note) attached to a specific message in a chat.
"""

import os
from pathlib import Path
from typing import Any

from ..client import get_telegram_client, run_async

NAME = "download_media"
DESCRIPTION = (
    "Download media attachments (photo, document, video, voice note) from a specific message ID in a chat. "
    "Saves to a specified local directory or defaults to 'downloads/telegram'."
)


async def _download_user_media(
    chat_id: str, message_id: int, output_dir: str | None = None
) -> str:
    """Async helper to download media from a message via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = int(chat_id) if (chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit())) else chat_id
        msg_id = int(message_id)

        msg = await client.get_messages(target, ids=msg_id)
        target_msg: Any = msg[0] if isinstance(msg, list) else msg

        if not target_msg or not getattr(target_msg, "media", None):
            await client.disconnect()
            return f"Error: Message ID {msg_id} in '{chat_id}' does not contain downloadable media."

        out_path = Path(output_dir or "downloads/telegram").resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        downloaded_file = await client.download_media(target_msg, file=str(out_path))
        await client.disconnect()

        if downloaded_file:
            file_size = os.path.getsize(downloaded_file) if os.path.exists(downloaded_file) else 0
            return (
                f"[OK] Downloaded media from message ID {msg_id} in '{chat_id}' "
                f"to '{downloaded_file}' ({file_size} bytes)."
            )
        return f"Error: Failed to download media from message ID {msg_id} in '{chat_id}'."

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to download media from message {message_id} in '{chat_id}': {e}"


def download_media(
    chat_id: str, message_id: int, output_dir: str | None = None
) -> str:
    """
    Download media attached to a Telegram message.

    Args:
        chat_id: Telegram chat ID, @username, or phone number.
        message_id: ID of the message containing media.
        output_dir: Optional directory path to save the media file. Defaults to 'downloads/telegram'.

    Returns:
        Confirmation message with output path and file size, or error message.
    """
    try:
        return run_async(_download_user_media, chat_id, message_id, output_dir)
    except Exception as e:
        return f"Error: {e}"
