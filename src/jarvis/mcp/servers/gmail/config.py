"""
Configuration and environment validation for Gmail MCP server.
"""

import os


def get_credentials() -> tuple[str, str]:
    """Get Gmail credentials from environment variables."""
    email_addr = os.environ.get("GMAIL_EMAIL", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not email_addr or not app_password:
        raise ValueError(
            "GMAIL_EMAIL and GMAIL_APP_PASSWORD environment variables must be set. "
            "Get an app password at https://myaccount.google.com/apppasswords"
        )
    return email_addr, app_password


def validate() -> list[str]:
    """Validate Gmail configuration."""
    errors = []
    if not os.environ.get("GMAIL_EMAIL"):
        errors.append("GMAIL_EMAIL is missing.")
    if not os.environ.get("GMAIL_APP_PASSWORD"):
        errors.append("GMAIL_APP_PASSWORD is missing.")
    return errors
