"""
Search emails tool for Gmail.
"""

import email
import imaplib

from ..config import get_credentials

NAME = "search_emails"
DESCRIPTION = "Search emails by keyword in Gmail via IMAP."


def search_emails(query: str, folder: str = "INBOX", count: int = 5) -> str:
    """
    Search emails by keyword in Gmail via IMAP.

    Args:
        query: Search keyword to look for in email subjects and bodies.
        folder: Mail folder to search in (default: INBOX).
        count: Maximum number of results (default: 5, max: 20).

    Returns:
        Formatted list of matching emails.
    """
    try:
        email_addr, app_password = get_credentials()
        count = min(count, 20)

        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            mail.login(email_addr, app_password)
            mail.select(folder, readonly=True)

            _, message_numbers = mail.search(None, f'(OR SUBJECT "{query}" BODY "{query}")')
            msg_nums = message_numbers[0].split()

            if not msg_nums:
                return f"🔍 No emails found matching '{query}'."

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

                results.append(
                    f"📧 From: {msg['From']}\n"
                    f"   Subject: {subject}\n"
                    f"   Date: {msg['Date']}\n"
                )

            return f"Found {len(results)} emails matching '{query}':\n\n" + "\n".join(results)

    except Exception as e:
        return f"❌ Search failed: {e}"
