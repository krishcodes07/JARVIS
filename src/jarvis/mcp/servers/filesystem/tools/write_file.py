"""
Write file tool for Filesystem.
"""

import os
from ..config import safe_path

NAME = "write_file"
DESCRIPTION = "Write content to a text file within the allowed directory."


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a text file. Creates the file if it doesn't exist.

    Args:
        path: File path relative to the allowed directory.
        content: The text content to write.
        encoding: Text encoding (default: utf-8).

    Returns:
        Success or error message.
    """
    try:
        filepath = safe_path(path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)

        return f"✅ Wrote {len(content):,} characters to {path}"

    except PermissionError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error writing file: {e}"
