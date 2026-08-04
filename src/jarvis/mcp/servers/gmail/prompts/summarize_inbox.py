"""
Prompt workflow for inbox summarization.
"""

NAME = "Summarize Inbox"
DESCRIPTION = "Workflow prompt to analyze recent inbox emails and generate key action items."
TEMPLATE = """Please review my Gmail inbox resource (gmail://inbox) and generate a clear, structured summary:

1. **High Priority Items**: Actionable emails requiring immediate response.
2. **Key Updates**: Information updates from team members or services.
3. **Follow-ups Needed**: Tasks or requests assigned to me.

Keep the summary concise, professional, and highlight sender names."""

ARGUMENTS = [
    {
        "name": "max_emails",
        "description": "Number of emails to summarize (default: 5)",
        "required": False,
    }
]


def get_prompt(max_emails: str = "5") -> str:
    """Generate the formatted prompt for summarization."""
    return TEMPLATE + f"\n\nLimit review to the top {max_emails} emails."
