"""
Reply email tool for Gmail.
Replies to a specific email by sender or subject.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import get_credentials

NAME = "reply_email"
DESCRIPTION = "Reply to an existing email by matching subject or sender."


def reply_email(
    to: str,
    subject: str,
    body: str,
    original_message_id: str = "",
    is_html: bool = False,
) -> str:
    """
    Send a reply email via Gmail SMTP with proper threading headers.

    Args:
        to: Recipient email address.
        subject: Original or reply subject line.
        body: Reply message body.
        original_message_id: Optional Message-ID header of original email for threading.
        is_html: If True, send HTML formatted reply.

    Returns:
        Confirmation or error message.
    """
    try:
        sender_email, app_password = get_credentials()

        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = to
        msg["Subject"] = reply_subject

        if original_message_id:
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id

        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)

        return f"↩️ Reply sent successfully to {to} (Subject: '{reply_subject}')"

    except Exception as e:
        return f"❌ Failed to send reply: {e}"
