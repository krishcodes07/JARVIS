"""
Delete email tool for Gmail.
Moves matching emails to Gmail Trash.
"""

import imaplib

from ..config import get_credentials

NAME = "delete_email"
DESCRIPTION = "Move matching emails to Gmail Trash by subject, sender, or keyword search."


def delete_email(query: str, folder: str = "INBOX", max_delete: int = 1) -> str:
    """
    Search and move matching emails to Gmail Trash.

    Args:
        query: Search keyword, subject, or sender email to identify target message(s).
        folder: Mail folder to search (default: INBOX).
        max_delete: Maximum number of matching emails to move to Trash (default: 1).

    Returns:
        Confirmation or error message.
    """
    try:
        email_addr, app_password = get_credentials()

        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            mail.login(email_addr, app_password)

            # Select folder with read-write access
            status, _ = mail.select(folder, readonly=False)
            if status != "OK":
                return f"❌ Mail folder '{folder}' not found."

            # Search by query
            search_crit = f'(OR SUBJECT "{query}" (OR FROM "{query}" BODY "{query}"))'
            _, message_numbers = mail.search(None, search_crit)
            msg_nums = message_numbers[0].split()

            if not msg_nums:
                return f"🔍 No emails found matching '{query}' in '{folder}'."

            # Take the requested number of target messages
            targets = msg_nums[-max_delete:]
            deleted_count = 0

            for num in targets:
                # Copy to Gmail Trash folder
                trash_folder = "[Gmail]/Trash"
                res, _ = mail.copy(num, trash_folder)
                if res == "OK":
                    # Mark original as deleted
                    mail.store(num, "+FLAGS", "\\Deleted")
                    deleted_count += 1

            mail.expunge()
            return f"🗑️ Moved {deleted_count} email(s) matching '{query}' to Trash."

    except Exception as e:
        return f"❌ Failed to delete email: {e}"
