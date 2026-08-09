"""
List Directory Tool — List directory contents with file metadata.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def safe_path(path: str) -> str:
    """Resolve file path to an absolute path."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return os.path.realpath(expanded)
    return os.path.realpath(os.path.join(os.getcwd(), expanded))


class ListDirectoryTool(BaseTool):
    """List directory contents with sizes and modification metadata."""

    schema = ToolSchema(
        name="list_directory",
        description="List all files and subdirectories inside a directory path, with sizes and metadata.",
        category="filesystem",
        aliases=["ls", "dir", "list_dir"],
        keywords=["list", "directory", "folder", "ls", "dir", "files"],
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Directory path to list (default: current working directory).",
                required=False,
                default=".",
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path") or "."

        try:
            dirpath = self.resolve_path(path)
            if not dirpath.exists():
                return f"Error: Directory not found: {path}"
            if not dirpath.is_dir():
                return f"Error: Path is a file, not a directory: {path}"

            entries = sorted(os.listdir(dirpath))
            if not entries:
                return f"Directory '{path}' is empty."

            lines = [f"Directory contents of '{path}' ({len(entries)} items):\n"]
            for entry in entries:
                full = dirpath / entry
                if full.is_dir():
                    lines.append(f"  [DIR]  {entry}/")
                else:
                    size = full.stat().st_size
                    lines.append(f"  [FILE] {entry} ({size:,} bytes)")

            return "\n".join(lines)

        except Exception as e:
            return f"Error listing directory '{path}': {e}"
