"""
Delete file tool for Filesystem — delete a file or directory.
"""

import os
import shutil
from ..config import safe_path

NAME = "delete_file"
DESCRIPTION = "Safely delete a file or directory."


def delete_file(path: str, recursive: bool = False) -> str:
    """
    Delete a file or directory.

    Args:
        path: File or directory path to delete.
        recursive: If True, delete non-empty directory trees.

    Returns:
        Status message.
    """
    try:
        filepath = safe_path(path)
        if not os.path.exists(filepath):
            return f"Error: Path not found: {path}"

        if os.path.isfile(filepath) or os.path.islink(filepath):
            os.remove(filepath)
            return f"Success: Deleted file '{path}'."

        if os.path.isdir(filepath):
            if recursive:
                shutil.rmtree(filepath)
                return f"Success: Recursively deleted directory '{path}'."
            else:
                os.rmdir(filepath)
                return f"Success: Deleted empty directory '{path}'."

        return f"Error: Cannot delete '{path}'."

    except Exception as e:
        return f"Error: Failed to delete '{path}': {e}"
