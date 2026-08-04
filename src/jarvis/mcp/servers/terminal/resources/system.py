"""
Terminal System Resource loader.
Exposes terminal://system
"""

from ..tools.get_system_info import get_system_info

URI = "terminal://system"
NAME = "Terminal System Overview"
DESCRIPTION = "Live information about the operating system, shell environment, and working directory."
MIME_TYPE = "text/plain"


def system() -> str:
    """Read terminal system overview as a contextual resource."""
    return get_system_info()
