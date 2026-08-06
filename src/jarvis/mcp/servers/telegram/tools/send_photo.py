"""
Send photo tool for Telegram MCP Server.
"""

import json
import urllib.request

from ..config import get_credentials

NAME = "send_photo"
DESCRIPTION = "Send a photo or image URL to a Telegram chat ID with an optional caption."


def send_photo(chat_id: str, photo_url: str, caption: str | None = "") -> str:
    """
    Send a photo URL to a Telegram chat.

    Args:
        chat_id: Telegram chat ID or @username.
        photo_url: Public HTTP/HTTPS URL of the image to send.
        caption: Optional text caption for the photo.

    Returns:
        Confirmation or error status message.
    """
    try:
        bot_token, _, _ = get_credentials()
        if not bot_token:
            return "Error: TELEGRAM_BOT_TOKEN environment variable is not configured."

        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption or "",
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                msg_id = res_data["result"]["message_id"]
                return f"[OK] Telegram photo sent to {chat_id} (Message ID: {msg_id})."
            else:
                return f"Error: Telegram API error: {res_data.get('description')}"

    except Exception as e:
        return f"Error: Failed to send photo: {e}"
