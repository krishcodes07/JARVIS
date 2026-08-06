"""
Get File Info Tool — Retrieve metadata and stat information for a file or directory.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def safe_path(path: str) -> str:
    """Resolve file path to an absolute path."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return os.path.realpath(expanded)
    return os.path.realpath(os.path.join(os.getcwd(), expanded))


class GetFileInfoTool(BaseTool):
    """Retrieve detailed metadata and file status information for a given path."""

    schema = ToolSchema(
        name="get_file_info",
        description="Get detailed metadata, size, timestamps, permissions, and stats for a file or directory.",
        category="filesystem",
        aliases=["file_info", "stat"],
        keywords=["info", "stat", "file", "metadata", "size", "created"],
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File or directory path.",
                required=True,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        if not path:
            return "Error: Path is required."

        try:
            filepath = safe_path(path)
            if not os.path.exists(filepath):
                return f"Error: Path not found: {path}"

            st = os.stat(filepath)
            is_dir = os.path.isdir(filepath)
            size = st.st_size
            created = time.ctime(st.st_ctime)
            modified = time.ctime(st.st_mtime)
            accessed = time.ctime(st.st_atime)

            lines = [
                f"Path Information for '{path}':",
                f"  • Absolute Path: {filepath}",
                f"  • Type: {'Directory' if is_dir else 'File'}",
                f"  • Size: {size:,} bytes",
                f"  • Created: {created}",
                f"  • Last Modified: {modified}",
                f"  • Last Accessed: {accessed}",
            ]

            if not is_dir:
                ext = os.path.splitext(filepath)[1]
                lines.append(f"  • Extension: '{ext}'")

            return "\n".join(lines)

        except Exception as e:
            return f"Error retrieving info for '{path}': {e}"
