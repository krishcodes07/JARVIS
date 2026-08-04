"""
Read emails tool for Gmail.
"""

import email
import imaplib

from ..config import get_credentials

NAME = "read_emails"
DESCRIPTION = "Read recent emails from Gmail via IMAP."


def read_emails(folder: str = "INBOX", count: int = 5) -> str:
    """
    Read recent emails from Gmail via IMAP.

    Args:
        folder: Mail folder to read from (default: INBOX).
        count: Number of recent emails to fetch (default: 5, max: 20).

    Returns:
        Formatted list of recent emails with sender, subject, date, and snippet.
    """
    try:
        email_addr, app_password = get_credentials()
        count = min(count, 20)

        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            mail.login(email_addr, app_password)
            mail.select(folder, readonly=True)

            _, message_numbers = mail.search(None, "ALL")
            msg_nums = message_numbers[0].split()

            if not msg_nums:
                return "📭 No emails found."

            recent_nums = msg_nums[-count:]
            recent_nums.reverse()

            results = []
            for num in recent_nums:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject_header = email.header.decode_header(msg["Subject"] or "(No Subject)")
                subject = ""
                for part, encoding in subject_header:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors="replace")
                    else:
                        subject += part

                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_text = payload.decode("utf-8", errors="replace")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")

                snippet = body_text[:200].replace("\n", " ").strip()

                results.append(
                    f"📧 From: {msg['From']}\n"
                    f"   Subject: {subject}\n"
                    f"   Date: {msg['Date']}\n"
                    f"   Preview: {snippet}...\n"
                )

            return f"Found {len(results)} emails:\n\n" + "\n".join(results)

    except imaplib.IMAP4.error as e:
        return f"❌ IMAP error: {e}"
    except Exception as e:
        return f"❌ Failed to read emails: {e}"
