"""
Get File Info Tool — Retrieve detailed metadata and stat information for a file or directory.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema, is_binary_file

logger = logging.getLogger(__name__)


class GetFileInfoTool(BaseTool):
    """Retrieve detailed metadata, size, timestamps, permissions, and stats for a given path."""

    schema = ToolSchema(
        name="get_file_info",
        description="Get detailed metadata, size, timestamps, permissions, and line/item counts for a file or directory.",
        category="filesystem",
        aliases=["file_info", "stat", "metadata"],
        keywords=["info", "stat", "file", "metadata", "size", "created", "modified"],
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
        """Execute get file info."""
        path = kwargs.get("path", "").strip()
        if not path:
            return "Error: Path is required."

        try:
            filepath = self.resolve_path(path)
            if not filepath.exists():
                return f"Error: Path not found: '{path}'"

            st = filepath.stat()
            is_dir = filepath.is_dir()
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

            if is_dir:
                try:
                    entries = list(filepath.iterdir())
                    lines.append(f"  • Direct Children: {len(entries)} items")
                except Exception:
                    pass
            else:
                ext = filepath.suffix or "[None]"
                is_bin = is_binary_file(filepath)
                lines.append(f"  • Extension: {ext}")
                lines.append(f"  • Binary File: {'Yes' if is_bin else 'No (Text)'}")
                if not is_bin:
                    try:
                        with open(filepath, encoding="utf-8", errors="ignore") as f:
                            line_count = sum(1 for _ in f)
                        lines.append(f"  • Total Lines: {line_count:,}")
                    except Exception:
                        pass

            return "\n".join(lines)

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error retrieving info for '%s': %s", path, e, exc_info=True)
            return f"Error retrieving info for '{path}': {e}"
