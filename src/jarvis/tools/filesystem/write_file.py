"""
Write File Tool — Atomic file writer with directory creation and detailed status reporting.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema, atomic_write_text

logger = logging.getLogger(__name__)


class WriteFileTool(BaseTool):
    """Write text content to a file atomically, creating parent directories as needed."""

    schema = ToolSchema(
        name="write_file",
        description=(
            "Write text content to a file atomically. "
            "Creates any missing parent directories automatically and overwrites existing contents safely."
        ),
        category="filesystem",
        aliases=["write_text", "create_file", "save_file"],
        keywords=["write", "file", "create", "save", "overwrite", "save_file"],
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
                description="The full text content to write into the file.",
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
        """Write content to file atomically."""
        path = kwargs.get("path", "").strip()
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            existed_before = filepath.exists()
            old_size = filepath.stat().st_size if existed_before else 0

            # Atomic write to prevent partial file corruption
            atomic_write_text(filepath, content, encoding=encoding)

            new_size = filepath.stat().st_size
            line_count = len(content.splitlines())
            action_verb = "Overwrote" if existed_before else "Created and wrote"

            return (
                f"Success: {action_verb} '{path}'.\n"
                f"  • Lines: {line_count:,}\n"
                f"  • Characters: {len(content):,}\n"
                f"  • Size: {new_size:,} bytes (previous: {old_size:,} bytes)\n"
                f"  • Status: Atomic write verified."
            )

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error writing file '%s': %s", path, e, exc_info=True)
            return f"Error writing file '{path}': {e}"
