"""
Read File Tool — Read contents of a text file with optional line range or max char limit.
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


class ReadFileTool(BaseTool):
    """Read the contents of a text file with line ranges or character limits."""

    schema = ToolSchema(
        name="read_file",
        description=(
            "Read contents of a text file with optional line range slicing (e.g. start_line=1, end_line=100) "
            "or max character caps. Reports file size and line counts."
        ),
        category="filesystem",
        aliases=["cat", "view_file", "read_text"],
        keywords=["read", "file", "view", "lines", "cat", "inspect"],
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File path (relative or absolute).",
                required=True,
            ),
            ToolParameter(
                name="start_line",
                type="integer",
                description="Optional 1-based starting line number.",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                type="integer",
                description="Optional 1-based ending line number.",
                required=False,
            ),
            ToolParameter(
                name="max_chars",
                type="integer",
                description="Optional maximum number of characters to return.",
                required=False,
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
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        max_chars = kwargs.get("max_chars")
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = safe_path(path)
            if not os.path.exists(filepath):
                return f"Error: File not found: {path}"
            if not os.path.isfile(filepath):
                return f"Error: Path is a directory, not a file: {path}"

            total_bytes = os.path.getsize(filepath)

            with open(filepath, encoding=encoding, errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            if total_lines == 0:
                return f"File '{path}' is empty (0 lines, 0 bytes)."

            s_line = 1 if (start_line is None or start_line < 1) else start_line
            e_line = total_lines if (end_line is None or end_line > total_lines) else end_line

            if s_line > total_lines:
                return (
                    f"File '{path}' metadata:\n"
                    f"  • Total Lines: {total_lines:,}\n"
                    f"  • Total Size: {total_bytes:,} bytes\n"
                    f"Warning: Requested start_line ({s_line}) exceeds total line count ({total_lines})."
                )

            if e_line < s_line:
                e_line = s_line

            slice_start = s_line - 1
            slice_end = e_line
            selected_lines = lines[slice_start:slice_end]

            content = "".join(selected_lines)
            cap = max_chars if (max_chars and max_chars > 0) else 100_000
            truncated_msg = ""
            if len(content) > cap:
                content = content[:cap]
                truncated_msg = f" (truncated at {cap:,} chars)"

            header = (
                f"File: {path}\n"
                f"Metadata: Total Lines: {total_lines:,} | Total Size: {total_bytes:,} bytes | "
                f"Showing Lines {s_line} to {e_line} of {total_lines:,}{truncated_msg}\n"
                f"{'=' * 60}\n"
            )

            return header + content

        except Exception as e:
            return f"Error reading file '{path}': {e}"
