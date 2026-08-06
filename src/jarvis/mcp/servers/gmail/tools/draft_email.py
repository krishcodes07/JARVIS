"""
Draft email tool for Gmail.
Creates or saves an email draft in Gmail without sending it immediately.
"""

import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import get_credentials

NAME = "draft_email"
DESCRIPTION = "Create and save an email draft in Gmail without sending it."


def draft_email(to: str, subject: str, body: str, is_html: bool = False) -> str:
    """
    Save an email draft to Gmail.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text or HTML.
        is_html: If True, format body as HTML. Default is plain text.

    Returns:
        Success or error message.
    """
    try:
        sender_email, app_password = get_credentials()

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = to
        msg["Subject"] = subject

        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))

        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            mail.login(sender_email, app_password)

            # Append to [Gmail]/Drafts folder
            draft_folder = "[Gmail]/Drafts"
            status, _ = mail.append(
                draft_folder,
                "\\Draft",
                imaplib.Time2Internaldate(time.time()),
                msg.as_bytes(),
            )

            if status == "OK":
                return f"📝 Draft saved successfully for recipient '{to}' with subject '{subject}'."
            else:
                return f"❌ Failed to save draft: IMAP returned {status}."

    except Exception as e:
        return f"❌ Error saving draft: {e}"
