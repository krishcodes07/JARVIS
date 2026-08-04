"""
Move file tool for Filesystem — move or rename files and directories.
"""

import os
import shutil
from ..config import safe_path

NAME = "move_file"
DESCRIPTION = "Move or rename a file or directory."


def move_file(source: str, destination: str, overwrite: bool = True) -> str:
    """
    Move or rename a file or directory.

    Args:
        source: Source file or folder path.
        destination: Destination file or folder path.
        overwrite: If True, overwrite destination if it exists.

    Returns:
        Status message.
    """
    try:
        src_path = safe_path(source)
        dst_path = safe_path(destination)

        if not os.path.exists(src_path):
            return f"Error: Source path not found: {source}"

        if os.path.exists(dst_path):
            if not overwrite:
                return f"Error: Destination '{destination}' already exists and overwrite=False."
            if os.path.isdir(dst_path):
                shutil.rmtree(dst_path)
            else:
                os.remove(dst_path)

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.move(src_path, dst_path)

        return f"Success: Moved '{source}' to '{destination}'."

    except Exception as e:
        return f"Error: Failed to move '{source}' to '{destination}': {e}"
