"""
Prompt workflow for sending formatted Telegram updates.
"""

NAME = "Send Telegram Update"
DESCRIPTION = "Workflow prompt template for sending formatted project or notification updates to a Telegram chat."
TEMPLATE = """Send the following update message to Telegram chat ID: {chat_id}

Message Details:
- Recipient Chat ID: {chat_id}
- Summary Content: {summary}

Instructions:
1. Format the message clearly using HTML or clean text.
2. Use the Telegram tool (send_message) to send the update.
3. Report execution status and result."""

ARGUMENTS = [
    {"name": "chat_id", "description": "Target Telegram Chat ID or @username", "required": True},
    {"name": "summary", "description": "Update text content or summary", "required": True},
]


def get_prompt(chat_id: str = "", summary: str = "") -> str:
    return TEMPLATE.format(chat_id=chat_id, summary=summary)
