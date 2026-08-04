"""
List directory tool for Filesystem.
"""

import os
from ..config import safe_path

NAME = "list_directory"
DESCRIPTION = "List files and folders in a directory."


def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """
    List files and folders in a directory.

    Args:
        path: Directory path relative to the allowed directory (default: root).
        show_hidden: If True, include hidden files (starting with '.').

    Returns:
        Formatted directory listing.
    """
    try:
        dirpath = safe_path(path)

        if not os.path.isdir(dirpath):
            return f"❌ Not a directory: {path}"

        entries = sorted(os.listdir(dirpath))

        if not show_hidden:
            entries = [e for e in entries if not e.startswith(".")]

        if not entries:
            return f"📁 Directory '{path}' is empty."

        lines = [f"📁 Contents of '{path}':"]
        for entry in entries:
            full = os.path.join(dirpath, entry)
            if os.path.isdir(full):
                lines.append(f"  📂 {entry}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"  📄 {entry} ({format_size(size)})")

        return "\n".join(lines)

    except PermissionError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error listing directory: {e}"
