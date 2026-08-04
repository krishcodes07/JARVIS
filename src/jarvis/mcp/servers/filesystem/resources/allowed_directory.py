"""
Filesystem Allowed Directory Resource loader.
Exposes filesystem://allowed_directory
"""

from ..config import ALLOWED_DIR
from ..tools.list_directory import list_directory

URI = "filesystem://allowed_directory"
NAME = "Allowed Workspace Directory"
DESCRIPTION = "Overview of files and subdirectories in the primary allowed workspace directory."
MIME_TYPE = "text/plain"


def allowed_directory() -> str:
    """Read the top-level directory listing as a contextual resource."""
    return f"Allowed Workspace Root: {ALLOWED_DIR}\n\n" + list_directory(".", show_hidden=False)
