"""
Read file tool for Filesystem.
"""

import os
from typing import Optional
from ..config import safe_path

NAME = "read_file"
DESCRIPTION = (
    "Read the contents of a text file with optional line ranges (e.g. start_line=100, end_line=200) "
    "or max character limits. Automatically includes total line count and file size metadata."
)


def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_chars: Optional[int] = None,
    encoding: str = "utf-8",
) -> str:
    """
    Read the contents of a text file, with optional line range or character limit.
    Reports total line count and total file size.

    Args:
        path: File path (relative or absolute).
        start_line: Optional 1-based starting line number (e.g. 1 or 100).
        end_line: Optional 1-based ending line number (e.g. 200).
        max_chars: Optional maximum number of characters to return.
        encoding: Text encoding (default: utf-8).

    Returns:
        Formatted file text with total line count, size, and requested content.
    """
    try:
        filepath = safe_path(path)
        if not os.path.exists(filepath):
            return f"Error: File not found: {path}"
        if not os.path.isfile(filepath):
            return f"Error: Not a file: {path}"

        total_bytes = os.path.getsize(filepath)

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        if total_lines == 0:
            return f"File '{path}' is empty (0 lines, 0 bytes)."

        # Determine line range (1-indexed for user/AI)
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

        # Slice lines (0-indexed array)
        slice_start = s_line - 1
        slice_end = e_line
        selected_lines = lines[slice_start:slice_end]

        content = "".join(selected_lines)

        # Apply character cap if max_chars is set or for safety fallback (100k chars)
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

    except PermissionError as e:
        return f"Error: {e}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode '{path}' with encoding '{encoding}'. File may be binary."
    except Exception as e:
        return f"Error: {e}"
