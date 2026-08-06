"""
Search messages tool for Telegram User Account (MTProto).
Searches for messages by keyword in a specific chat or globally across all chats.
"""


from ..client import get_telegram_client, run_async

NAME = "search_messages"
DESCRIPTION = (
    "Search for messages containing a keyword or text query in a specific Telegram chat "
    "or across all chats."
)


async def _search_user_messages(query: str, chat_id: str | None = None, limit: int = 15) -> str:
    """Async helper to search messages via Telethon."""
    client = get_telegram_client()
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return "Error: Telegram user session is not authorized. Please run login script."

    try:
        target = None
        if chat_id and chat_id.strip():
            cid = chat_id.strip()
            target = int(cid) if (cid.isdigit() or (cid.startswith("-") and cid[1:].isdigit())) else cid

        messages = await client.get_messages(target, search=query, limit=limit)
        await client.disconnect()

        if not messages:
            target_desc = f"in chat '{chat_id}'" if chat_id else "across your chats"
            return f"Telegram: No messages matching '{query}' were found {target_desc}."

        target_desc = f"in '{chat_id}'" if chat_id else "across your Telegram chats"
        output = [f"🔍 Found {len(messages)} message(s) matching '{query}' {target_desc}:\n"]

        for m in messages:
            sender_id = m.sender_id or "Unknown"
            date_str = m.date.strftime("%Y-%m-%d %H:%M:%S") if m.date else "N/A"
            text_snippet = (m.text or "[Media/Attachment]").replace("\n", " ")
            if len(text_snippet) > 100:
                text_snippet = text_snippet[:97] + "..."

            output.append(f"  • [ID: {m.id}] ({date_str}) Sender: {sender_id}: {text_snippet}")

        return "\n".join(output)

    except Exception as e:
        await client.disconnect()
        return f"Error: Failed to search Telegram messages: {e}"


def search_messages(query: str, chat_id: str | None = None, limit: int = 15) -> str:
    """
    Search for messages containing text matching query.

    Args:
        query: Text search term or keyword.
        chat_id: Optional specific chat ID or @username to search inside (leave blank to search globally).
        limit: Maximum number of search results to return (default: 15).

    Returns:
        Formatted summary of matching messages.
    """
    try:
        return run_async(_search_user_messages, query, chat_id, limit)
    except Exception as e:
        return f"Error: {e}"
