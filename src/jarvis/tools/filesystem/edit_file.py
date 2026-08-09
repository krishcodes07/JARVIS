"""
Edit File Tool — Edit specific line ranges or perform text substitution in a file.
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


class EditFileTool(BaseTool):
    """Edit specific line ranges in a file or perform string search and replace."""

    schema = ToolSchema(
        name="edit_file",
        description=(
            "Edit specific line ranges in a file (e.g. replace lines 30 to 100) or perform "
            "string find-and-replace without rewriting the entire file."
        ),
        category="filesystem",
        aliases=["modify_file", "replace_in_file", "patch_file"],
        keywords=["edit", "replace", "patch", "lines", "find", "modify"],
        dangerous=True,
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
                description="Optional 1-based start line number to replace.",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                type="integer",
                description="Optional 1-based end line number to replace.",
                required=False,
            ),
            ToolParameter(
                name="new_content",
                type="string",
                description="Replacement text for line range editing.",
                required=False,
                default="",
            ),
            ToolParameter(
                name="find_text",
                type="string",
                description="Optional literal text to search for.",
                required=False,
            ),
            ToolParameter(
                name="replace_text",
                type="string",
                description="Optional text to replace find_text with.",
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
        new_content = kwargs.get("new_content") or ""
        find_text = kwargs.get("find_text")
        replace_text = kwargs.get("replace_text")
        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            if not filepath.exists():
                return f"Error: File not found: {path}"

            with open(filepath, encoding=encoding, errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Mode A: Line Range Replacement
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
            return f"Error editing file '{path}': {e}"
