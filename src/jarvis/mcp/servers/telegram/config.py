"""
Configuration and credentials helper for Telegram MCP Server.
"""

import os
from typing import List, Tuple


def get_credentials() -> Tuple[str, str, str]:
    """
    Get Telegram credentials from environment variables.
    Supports Telegram Bot API (TELEGRAM_BOT_TOKEN) or MTProto (TELEGRAM_API_ID, TELEGRAM_API_HASH).
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    api_id = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    return bot_token, api_id, api_hash


def validate() -> List[str]:
    """Validate Telegram server configuration."""
    errors = []
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    api_id = os.environ.get("TELEGRAM_API_ID", "")
    if not bot_token and not api_id:
        errors.append("TELEGRAM_BOT_TOKEN or TELEGRAM_API_ID environment variable is missing.")
    return errors
