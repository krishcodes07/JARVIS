"""
Get file info tool for Filesystem.
"""

from datetime import datetime
import os
from ..config import safe_path
from .list_directory import format_size

NAME = "get_file_info"
DESCRIPTION = "Get metadata about a file or directory."


def get_file_info(path: str) -> str:
    """
    Get metadata about a file or directory.

    Args:
        path: File or directory path relative to the allowed directory.

    Returns:
        File metadata (size, dates, type).
    """
    try:
        filepath = safe_path(path)
        stat = os.stat(filepath)

        is_dir = os.path.isdir(filepath)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

        info = [
            f"📋 Info for '{path}':",
            f"  Type: {'Directory' if is_dir else 'File'}",
            f"  Size: {format_size(stat.st_size)}",
            f"  Modified: {modified}",
            f"  Created: {created}",
        ]

        if is_dir:
            count = len(os.listdir(filepath))
            info.append(f"  Items: {count}")

        return "\n".join(info)

    except PermissionError as e:
        return f"❌ {e}"
    except FileNotFoundError:
        return f"❌ Not found: {path}"
    except Exception as e:
        return f"❌ Error: {e}"
