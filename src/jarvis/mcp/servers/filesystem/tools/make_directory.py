"""
Make directory tool for Filesystem.
"""

import os
from ..config import safe_path

NAME = "make_directory"
DESCRIPTION = "Create a new directory (including parent directories)."


def make_directory(path: str) -> str:
    """
    Create a new directory (including parent directories).

    Args:
        path: Directory path relative to the allowed directory.

    Returns:
        Success or error message.
    """
    try:
        dirpath = safe_path(path)
        os.makedirs(dirpath, exist_ok=True)
        return f"✅ Created directory: {path}"
    except PermissionError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error creating directory: {e}"
