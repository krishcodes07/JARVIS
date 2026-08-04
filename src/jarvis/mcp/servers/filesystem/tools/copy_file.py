"""
Copy file tool for Filesystem — copy files or directories.
"""

import os
import shutil
from ..config import safe_path

NAME = "copy_file"
DESCRIPTION = "Copy a file or directory tree from source to destination."


def copy_file(source: str, destination: str, overwrite: bool = True) -> str:
    """
    Copy a file or folder from source to destination.

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

        if os.path.exists(dst_path) and not overwrite:
            return f"Error: Destination '{destination}' already exists and overwrite=False."

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        if os.path.isdir(src_path):
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            return f"Success: Copied directory '{source}' to '{destination}'."
        else:
            shutil.copy2(src_path, dst_path)
            return f"Success: Copied file '{source}' to '{destination}'."

    except Exception as e:
        return f"Error: Failed to copy '{source}' to '{destination}': {e}"
