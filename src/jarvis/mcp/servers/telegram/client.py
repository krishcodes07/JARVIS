"""
Telethon client runner for Telegram User Account (MTProto User API).
Allows sending and reading messages from your personal Telegram user account.
"""

import asyncio
import os
from typing import Any, Callable, Coroutine
from telethon import TelegramClient
from telethon.sessions import StringSession

from .config import get_credentials


def get_telegram_client() -> TelegramClient:
    """Instantiate Telethon TelegramClient using user API credentials and Session string or file."""
    bot_token, api_id, api_hash = get_credentials()

    if not api_id or not api_hash:
        raise ValueError(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be configured. "
            "Get your API credentials at https://my.telegram.org/apps"
        )

    session_str = os.environ.get("TELEGRAM_SESSION_STRING", "").strip()
    session_file = os.environ.get("TELEGRAM_SESSION_FILE", "telegram_user.session").strip()

    if session_str:
        session = StringSession(session_str)
    else:
        # Resolve path relative to mcp_servers/telegram or current directory
        session = session_file

    return TelegramClient(session, int(api_id), api_hash)


def run_async(coro_fn: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs) -> Any:
    """Execute an async Telethon function in a fresh or existing event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Handle case where loop is already running in current thread
        import nest_asyncio
        nest_asyncio.apply()

    return loop.run_until_complete(coro_fn(*args, **kwargs))
