"""
Edit file tool for Filesystem — edit specific line ranges or perform find/replace.
"""

import os
from typing import Optional
from ..config import safe_path

NAME = "edit_file"
DESCRIPTION = (
    "Edit specific line ranges in a text file (e.g. replace lines 30 to 100 with new_content) "
    "or perform target text find-and-replace. Avoids rewriting the entire file."
)


def edit_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    new_content: str = "",
    find_text: Optional[str] = None,
    replace_text: Optional[str] = None,
    encoding: str = "utf-8",
) -> str:
    """
    Edit a file by line range or by string replacement.

    Args:
        path: File path (relative or absolute).
        start_line: Optional 1-based start line number to replace (e.g. 30).
        end_line: Optional 1-based end line number to replace (e.g. 100).
        new_content: Replacement text content for the line range.
        find_text: Optional literal text string to search for.
        replace_text: Optional text to replace find_text with.
        encoding: File encoding (default: utf-8).

    Returns:
        Status message with total line count and modification summary.
    """
    try:
        filepath = safe_path(path)
        if not os.path.exists(filepath):
            return f"Error: File not found: {path}"

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Mode A: Line Range Replacement (e.g. lines 30-100)
        if start_line is not None:
            s_line = max(1, start_line)
            e_line = total_lines if (end_line is None or end_line > total_lines) else max(s_line, end_line)

            if s_line > total_lines + 1:
                return f"Error: start_line ({s_line}) exceeds file line count ({total_lines})."

            slice_start = s_line - 1
            slice_end = min(total_lines, e_line)

            replacement_lines = new_content.splitlines(keepends=True)
            if replacement_lines and not replacement_lines[-1].endswith("\n"):
                replacement_lines[-1] += "\n"

            new_file_lines = lines[:slice_start] + replacement_lines + lines[slice_end:]

            with open(filepath, "w", encoding=encoding) as f:
                f.writelines(new_file_lines)

            replaced_count = slice_end - slice_start
            return (
                f"Success: Updated '{path}'. Replaced lines {s_line} to {slice_end} ({replaced_count} lines) "
                f"with {len(replacement_lines)} new lines. Total lines now: {len(new_file_lines):,}."
            )

        # Mode B: Find and Replace String Substitution
        if find_text is not None:
            full_text = "".join(lines)
            occurrences = full_text.count(find_text)
            if occurrences == 0:
                return f"Notice: Target text '{find_text}' not found in '{path}'."

            target_replace = replace_text if replace_text is not None else ""
            modified_text = full_text.replace(find_text, target_replace)

            with open(filepath, "w", encoding=encoding) as f:
                f.write(modified_text)

            new_total_lines = len(modified_text.splitlines())
            return (
                f"Success: Replaced {occurrences} occurrence(s) of '{find_text}' in '{path}'. "
                f"Total lines now: {new_total_lines:,}."
            )

        return "Error: Specify either start_line (with optional end_line & new_content) or find_text & replace_text."

    except Exception as e:
        return f"Error: Failed to edit file: {e}"
