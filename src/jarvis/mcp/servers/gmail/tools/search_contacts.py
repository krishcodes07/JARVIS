"""
Search contacts tool for Gmail.
Searches previous sent and received emails to discover email addresses for a given name.
"""

import email
from email.utils import parseaddr
import imaplib
import re
from typing import Dict, List, Set, Tuple

from ..config import get_credentials

NAME = "search_contacts"
DESCRIPTION = (
    "Search previous emails (sent & received) to find the email address associated with a person's name "
    "(e.g. searching 'Aryan' to find 'aryan@example.com')."
)


def _extract_contacts_from_folder(
    mail: imaplib.IMAP4_SSL, folder: str, query_name: str, max_fetch: int = 15
) -> List[Tuple[str, str]]:
    """Helper to search a mail folder and parse From/To contact info."""
    contacts: List[Tuple[str, str]] = []
    try:
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            return contacts

        # Search for query in headers or body
        search_criterion = f'(OR FROM "{query_name}" (OR TO "{query_name}" SUBJECT "{query_name}"))'
        _, message_numbers = mail.search(None, search_criterion)
        msg_nums = message_numbers[0].split()

        if not msg_nums:
            # Fallback search ALL if name search yielded no direct results
            _, message_numbers = mail.search(None, "ALL")
            msg_nums = message_numbers[0].split()

        recent_nums = msg_nums[-max_fetch:]
        recent_nums.reverse()

        for num in recent_nums:
            _, msg_data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC)])")
            if not msg_data or not msg_data[0]:
                continue
            raw_headers = msg_data[0][1]
            if isinstance(raw_headers, bytes):
                msg = email.message_from_bytes(raw_headers)
                for header_key in ["From", "To", "Cc"]:
                    header_val = msg.get(header_key)
                    if header_val:
                        display_name, email_addr = parseaddr(header_val)
                        if email_addr and "@" in email_addr:
                            # Filter if query matches name or email address
                            if (
                                query_name.lower() in display_name.lower()
                                or query_name.lower() in email_addr.lower()
                            ):
                                contacts.append((display_name or email_addr.split("@")[0], email_addr))
    except Exception:
        pass
    return contacts


def search_contacts(name: str, count: int = 10) -> str:
    """
    Search previous emails (sent and inbox) to find email addresses associated with a person's name.

    Args:
        name: Name or keyword of the contact to search for (e.g., "Aryan", "John").
        count: Maximum number of contact results to return.

    Returns:
        Formatted list of matching contacts with display name and email address.
    """
    try:
        email_addr, app_password = get_credentials()
        name_clean = name.strip()

        if not name_clean:
            return "❌ Please specify a name or keyword to search for."

        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            mail.login(email_addr, app_password)

            all_raw = []
            # Search both Sent Mail and INBOX for comprehensive coverage
            for folder in ["[Gmail]/Sent Mail", "INBOX"]:
                all_raw.extend(_extract_contacts_from_folder(mail, folder, name_clean))

            # Deduplicate contacts by email address (case-insensitive)
            seen_emails: Set[str] = set()
            unique_contacts: List[Tuple[str, str]] = []

            for display_name, addr in all_raw:
                addr_lower = addr.lower()
                # Skip user's own email address
                if addr_lower == email_addr.lower():
                    continue
                if addr_lower not in seen_emails:
                    seen_emails.add(addr_lower)
                    unique_contacts.append((display_name, addr))
                    if len(unique_contacts) >= count:
                        break

            if not unique_contacts:
                return (
                    f"🔍 No previous contacts found matching '{name_clean}'.\n"
                    f"Tip: Ask the user for {name_clean}'s exact email address."
                )

            lines = [f"📇 Found {len(unique_contacts)} contact(s) matching '{name_clean}':\n"]
            for d_name, addr in unique_contacts:
                lines.append(f"  • {d_name} <{addr}>")

            lines.append("\nYou can use these email addresses directly when calling send_email.")
            return "\n".join(lines)

    except Exception as e:
        return f"❌ Search contacts failed: {e}"
