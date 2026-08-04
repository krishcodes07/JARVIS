"""
Send email tool for Gmail.
"""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from ..config import get_credentials

NAME = "send_email"
DESCRIPTION = "Send an email via Gmail SMTP."


def send_email(to: str, subject: str, body: str, is_html: bool = False) -> str:
    """
    Send an email via Gmail SMTP.

    Args:
        to: Recipient email address (comma-separated for multiple).
        subject: Email subject line.
        body: Email body content.
        is_html: If True, send as HTML email. Default is plain text.

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

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)

        return f"✅ Email sent successfully to {to}"

    except smtplib.SMTPAuthenticationError:
        return "❌ Authentication failed. Check your GMAIL_EMAIL and GMAIL_APP_PASSWORD."
    except Exception as e:
        return f"❌ Failed to send email: {e}"
