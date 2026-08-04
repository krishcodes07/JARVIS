"""
Interactive Login Script for Telegram User Account (Telethon).

Run this script once in your terminal to log into your personal Telegram account:
    python -m jarvis.mcp.servers.telegram.login
"""

import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load env variables
load_dotenv()


async def main():
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()

    print("\n========================================================")
    print(" âœˆï¸  Telegram User Account Login (Telethon)")
    print("========================================================\n")

    if not api_id:
        api_id = input("Enter your TELEGRAM_API_ID (from https://my.telegram.org): ").strip()
    if not api_hash:
        api_hash = input("Enter your TELEGRAM_API_HASH (from https://my.telegram.org): ").strip()

    if not api_id or not api_hash:
        print("\nâŒ Error: API ID and API Hash are required!")
        sys.exit(1)

    print("\n[>] Connecting to Telegram...")
    session = StringSession()
    client = TelegramClient(session, int(api_id), api_hash)

    # Telethon's start() returns a coroutine at runtime when loop is running,
    # but is typed as returning TelegramClient, causing a type checker warning.
    await client.start()  # type: ignore

    me = await client.get_me()
    session_str = session.save()

    print("\nâœ… Successfully Logged In to Personal Telegram Account!")
    print(f"  â€¢ Name: {me.first_name} {me.last_name or ''}")
    print(f"  â€¢ Username: @{me.username or 'N/A'}")
    print(f"  â€¢ Phone: +{me.phone}")
    print(f"  â€¢ Account ID: {me.id}\n")

    print("=" * 60)
    print("ðŸ”‘ YOUR TELEGRAM_SESSION_STRING:")
    print("=" * 60)
    print(session_str)
    print("=" * 60)
    print("\nðŸ“Œ Copy the TELEGRAM_SESSION_STRING above and set it in your .env or mcp_config.json:")
    print(f"   TELEGRAM_API_ID={api_id}")
    print(f"   TELEGRAM_API_HASH={api_hash}")
    print(f"   TELEGRAM_SESSION_STRING={session_str}\n")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

