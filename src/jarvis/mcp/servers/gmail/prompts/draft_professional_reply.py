"""
Prompt workflow for drafting professional email replies.
"""

NAME = "Draft Professional Reply"
DESCRIPTION = "Workflow prompt to draft a polished professional email response."
TEMPLATE = """Please compose a clear, polite, and professional email response to the following message:

Sender: {sender}
Subject: {subject}
Key Message Context: {context}

Requirements:
- Professional tone suitable for business communication
- Include a clear call to action or resolution step
- Format with standard greeting and sign-off"""

ARGUMENTS = [
    {"name": "sender", "description": "Name or email of the sender", "required": True},
    {"name": "subject", "description": "Original email subject line", "required": True},
    {"name": "context", "description": "Brief note on what you want to reply", "required": True},
]


def get_prompt(sender: str = "", subject: str = "", context: str = "") -> str:
    """Generate the formatted draft prompt."""
    return TEMPLATE.format(sender=sender, subject=subject, context=context)
