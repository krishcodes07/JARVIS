"""
Write File Tool — Write content to a text file.
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


class WriteFileTool(BaseTool):
    """Write text content to a file, creating parent directories as needed."""

    schema = ToolSchema(
        name="write_file",
        description="Write text content to a file. Overwrites existing contents or creates a new file.",
        category="filesystem",
        aliases=["write_text", "create_file", "save_file"],
        keywords=["write", "file", "create", "save", "overwrite"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File path (relative or absolute).",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="The text content to write into the file.",
                required=True,
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="File encoding (default: utf-8).",
                required=False,
                default="utf-8",
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)

            return f"Wrote {len(content):,} characters to '{path}'."

        except Exception as e:
            return f"Error writing file '{path}': {e}"
