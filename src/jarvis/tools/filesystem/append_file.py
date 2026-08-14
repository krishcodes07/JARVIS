"""
Append File Tool — Append text content to a file with newline handling and status verification.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class AppendFileTool(BaseTool):
    """Append text content to the end of a file."""

    schema = ToolSchema(
        name="append_file",
        description="Append text content to the end of an existing or new file.",
        category="filesystem",
        aliases=["append_text", "add_to_file"],
        keywords=["append", "add", "file", "text", "log", "write"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File path (relative to workspace or absolute).",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Text content to append to the file.",
                required=True,
            ),
            ToolParameter(
                name="ensure_newline",
                type="boolean",
                description="Whether to ensure content starts on a new line if file doesn't end with one (default: true).",
                required=False,
                default=True,
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
        """Execute file append."""
        path = kwargs.get("path", "").strip()
        content = kwargs.get("content", "")
        ensure_newline = kwargs.get("ensure_newline", True)
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            prefix = ""
            if ensure_newline and filepath.exists() and filepath.stat().st_size > 0:
                try:
                    with open(filepath, "rb") as f:
                        f.seek(-1, 2)
                        last_byte = f.read(1)
                        if last_byte != b"\n":
                            prefix = "\n"
                except Exception:
                    pass

            text_to_append = prefix + content

            with open(filepath, "a", encoding=encoding) as f:
                f.write(text_to_append)

            new_size = filepath.stat().st_size
            lines_added = len(text_to_append.splitlines())

            return (
                f"Success: Appended {len(content):,} characters ({lines_added} lines) to '{path}'.\n"
                f"  • Total File Size Now: {new_size:,} bytes."
            )

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error appending to file '%s': %s", path, e, exc_info=True)
            return f"Error appending to file '{path}': {e}"
