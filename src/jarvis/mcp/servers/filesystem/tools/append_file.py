"""
Append file tool for Filesystem — appends content to the end of a file.
"""

import os
from ..config import safe_path

NAME = "append_file"
DESCRIPTION = "Append text content to the end of an existing file without overwriting previous content."


def append_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Append text content to the end of a file.

    Args:
        path: File path (relative or absolute).
        content: Text content to append.
        encoding: File encoding (default: utf-8).

    Returns:
        Status message.
    """
    try:
        filepath = safe_path(path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "a", encoding=encoding) as f:
            f.write(content)

        return f"Success: Appended {len(content):,} characters to '{path}'."
    except Exception as e:
        return f"Error: Failed to append to file: {e}"
