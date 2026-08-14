"""
Read File Tool — Line-numbered file reader with binary detection, encoding fallbacks, and range slicing.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema, is_binary_file

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """Read contents of a text file with line numbers, slicing ranges, or max character limits."""

    schema = ToolSchema(
        name="read_file",
        description=(
            "Read contents of a text file with line numbers (e.g. '1: def foo():') for precise inspection. "
            "Supports line range slicing (start_line, end_line) and character limits. "
            "Automatically detects and protects against dumping raw binary files."
        ),
        category="filesystem",
        aliases=["cat", "view_file", "read_text", "view"],
        keywords=["read", "file", "view", "lines", "cat", "inspect", "open", "code"],
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File path to read (relative to workspace or absolute).",
                required=True,
            ),
            ToolParameter(
                name="start_line",
                type="integer",
                description="Optional 1-based starting line number (default: 1).",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                type="integer",
                description="Optional 1-based ending line number (inclusive).",
                required=False,
            ),
            ToolParameter(
                name="show_line_numbers",
                type="boolean",
                description="Whether to prefix each line with its 1-based line number (default: true).",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="max_chars",
                type="integer",
                description="Optional maximum number of characters to return (default: 80,000).",
                required=False,
                default=80_000,
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="File encoding (default: utf-8 with automatic fallback).",
                required=False,
                default="utf-8",
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute file read with safety, line numbers, and metadata."""
        path = kwargs.get("path", "").strip()
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        show_line_numbers = kwargs.get("show_line_numbers", True)
        max_chars = kwargs.get("max_chars") or 80_000
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            if not filepath.exists():
                return f"Error: File not found: '{path}'"
            if not filepath.is_file():
                return f"Error: Path is a directory, not a regular file: '{path}'"

            total_bytes = filepath.stat().st_size

            # Check if binary file
            if is_binary_file(filepath):
                return (
                    f"Binary File Notice:\n"
                    f"File: '{path}' ({filepath.name})\n"
                    f"Size: {total_bytes:,} bytes\n"
                    f"Type: Binary file (non-text). Cannot display raw contents in text context."
                )

            # Read file with fallback encodings
            lines = self._read_text_lines(filepath, encoding)
            total_lines = len(lines)

            if total_lines == 0:
                return f"File '{path}' is empty (0 lines, 0 bytes)."

            s_line = 1 if (start_line is None or start_line < 1) else start_line
            e_line = total_lines if (end_line is None or end_line > total_lines) else end_line

            if s_line > total_lines:
                return (
                    f"File: '{path}'\n"
                    f"Metadata: Total Lines: {total_lines:,} | Size: {total_bytes:,} bytes\n"
                    f"Warning: Requested start_line ({s_line}) exceeds total line count ({total_lines})."
                )

            if e_line < s_line:
                e_line = s_line

            slice_start = s_line - 1
            slice_end = e_line
            selected_lines = lines[slice_start:slice_end]

            # Format with line numbers if enabled
            formatted_lines = []
            for idx, line in enumerate(selected_lines, start=s_line):
                # Strip trailing newline for formatting, then add it back
                clean_line = line.rstrip("\r\n")
                if show_line_numbers:
                    formatted_lines.append(f"{idx:4d}: {clean_line}\n")
                else:
                    formatted_lines.append(f"{clean_line}\n")

            content = "".join(formatted_lines)
            truncated_msg = ""
            if len(content) > max_chars:
                content = content[:max_chars]
                truncated_msg = f" [Truncated at {max_chars:,} chars. Specify start_line/end_line to read in chunks]"

            header = (
                f"File: {path}\n"
                f"Lines {s_line}–{e_line} of {total_lines:,} | Size: {total_bytes:,} bytes{truncated_msg}\n"
                f"{'=' * 60}\n"
            )

            return header + content

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error reading file '%s': %s", path, e, exc_info=True)
            return f"Error reading file '{path}': {e}"

    def _read_text_lines(self, filepath: Any, requested_encoding: str) -> list[str]:
        """Read file lines with encoding fallback."""
        encodings = [requested_encoding, "utf-8", "utf-8-sig", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                with open(filepath, encoding=enc) as f:
                    return f.readlines()
            except UnicodeDecodeError:
                continue
            except Exception:
                break

        # Ultimate fallback with replacement
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return f.readlines()
