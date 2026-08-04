"""
Get bot info tool for Telegram MCP Server.
"""

import json
import urllib.request

from ..config import get_credentials

NAME = "get_bot_info"
DESCRIPTION = "Retrieve Telegram bot profile details, bot username, and connection status."


def get_bot_info() -> str:
    """
    Get Telegram bot information via getMe endpoint.

    Returns:
        Formatted summary of Telegram bot profile.
    """
    try:
        bot_token, _, _ = get_credentials()
        if not bot_token:
            return "Error: TELEGRAM_BOT_TOKEN environment variable is not configured."

        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        req = urllib.request.Request(url, headers={"User-Agent": "MCP-Telegram-Client/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                bot = res_data["result"]
                return (
                    f"🤖 Telegram Bot Info:\n"
                    f"  • Bot Name: {bot.get('first_name')}\n"
                    f"  • Username: @{bot.get('username')}\n"
                    f"  • Bot ID: {bot.get('id')}\n"
                    f"  • Can Join Groups: {bot.get('can_join_groups')}\n"
                    f"  • Status: Active & Connected"
                )
            else:
                return f"Error: Telegram API error: {res_data.get('description')}"

    except Exception as e:
        return f"Error: Failed to get bot info: {e}"
