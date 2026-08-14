"""
Edit File Tool — Industry-grade in-place file editor with unified diff generation, exact matching, and atomic writes.
"""

from __future__ import annotations

import ast
import json
import logging
from typing import Any

from jarvis.tools.base import (
    BaseTool,
    ToolParameter,
    ToolSchema,
    atomic_write_text,
    format_unified_diff,
    is_binary_file,
)

logger = logging.getLogger(__name__)


class EditFileTool(BaseTool):
    """Edit files via exact string replacement or line range substitution, returning unified diffs."""

    schema = ToolSchema(
        name="edit_file",
        description=(
            "Edit specific sections of a file in-place and return a unified diff. "
            "Supports two modes: "
            "(1) Exact string replacement (target_content/find_text -> replacement_content/replace_text with uniqueness checks); "
            "(2) Line range editing (start_line, end_line, new_content). "
            "Uses atomic file writes and checks for syntax errors."
        ),
        category="filesystem",
        aliases=["modify_file", "replace_in_file", "patch_file", "replace"],
        keywords=["edit", "replace", "patch", "lines", "find", "modify", "code", "substitute"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="File path to edit (relative to workspace or absolute).",
                required=True,
            ),
            ToolParameter(
                name="target_content",
                type="string",
                description="Exact literal text to search for and replace (alias: find_text).",
                required=False,
            ),
            ToolParameter(
                name="replacement_content",
                type="string",
                description="Replacement text to substitute for target_content (alias: replace_text).",
                required=False,
            ),
            ToolParameter(
                name="allow_multiple",
                type="boolean",
                description="If true, replace all occurrences of target_content; if false, fail if target_content is not unique (default: false).",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="start_line",
                type="integer",
                description="Optional 1-based start line number for line range replacement.",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                type="integer",
                description="Optional 1-based end line number for line range replacement.",
                required=False,
            ),
            ToolParameter(
                name="new_content",
                type="string",
                description="Replacement content for line range editing.",
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
        """Execute file edit and return unified diff."""
        path = kwargs.get("path", "").strip()
        target_content = kwargs.get("target_content") or kwargs.get("find_text")
        replacement_content = kwargs.get("replacement_content") if "replacement_content" in kwargs else kwargs.get("replace_text")
        allow_multiple = bool(kwargs.get("allow_multiple", False))

        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        new_content = kwargs.get("new_content")

        encoding = kwargs.get("encoding") or "utf-8"

        if not path:
            return "Error: File path is required."

        try:
            filepath = self.resolve_path(path)
            if not filepath.exists():
                return f"Error: File not found: '{path}'"
            if not filepath.is_file():
                return f"Error: Path is a directory, not a file: '{path}'"
            if is_binary_file(filepath):
                return f"Error: Cannot edit binary file: '{path}'"

            with open(filepath, encoding=encoding, errors="replace") as f:
                original_text = f.read()

            modified_text: str | None = None
            action_desc: str = ""

            # Mode A: Exact String Replacement
            if target_content is not None:
                if replacement_content is None:
                    replacement_content = ""

                # Normalize line endings in target for consistent matching
                normalized_orig = original_text.replace("\r\n", "\n")
                normalized_target = target_content.replace("\r\n", "\n")
                normalized_replacement = replacement_content.replace("\r\n", "\n")

                match_count = normalized_orig.count(normalized_target)

                if match_count == 0:
                    # Provide helpful context for why it failed
                    snippet = normalized_target[:60].replace("\n", "\\n")
                    return (
                        f"Edit Failed: Target content was not found in '{path}'.\n"
                        f"Target query: `{snippet}...`\n"
                        f"Tip: Ensure exact whitespace and indentation match the file. "
                        f"Use 'read_file' with show_line_numbers=True to verify current content."
                    )

                if match_count > 1 and not allow_multiple:
                    # Find line numbers of all matches
                    lines = normalized_orig.splitlines()
                    first_line_target = normalized_target.splitlines()[0] if normalized_target else ""
                    match_lines = [
                        idx + 1 for idx, l in enumerate(lines) if first_line_target in l
                    ]
                    lines_str = ", ".join(str(l) for l in match_lines[:5])
                    return (
                        f"Edit Failed: Target content matches {match_count} locations in '{path}' (lines {lines_str}).\n"
                        f"Safety Protection: Refusing ambiguous edit without unique match. "
                        f"Include more surrounding lines in 'target_content' to make it unique, or set 'allow_multiple=True'."
                    )

                if allow_multiple:
                    modified_text = normalized_orig.replace(normalized_target, normalized_replacement)
                    action_desc = f"Replaced {match_count} occurrence(s)"
                else:
                    # Replace only the first occurrence
                    modified_text = normalized_orig.replace(normalized_target, normalized_replacement, 1)
                    action_desc = "Replaced 1 occurrence"

                # Restore original line ending style if CRLF was used
                if "\r\n" in original_text:
                    modified_text = modified_text.replace("\n", "\r\n")

            # Mode B: Line Range Replacement
            elif start_line is not None:
                orig_lines = original_text.splitlines(keepends=True)
                total_lines = len(orig_lines)

                s_line = max(1, start_line)
                e_line = total_lines if (end_line is None or end_line > total_lines) else max(s_line, end_line)

                if s_line > total_lines + 1:
                    return f"Error: start_line ({s_line}) exceeds file line count ({total_lines})."

                slice_start = s_line - 1
                slice_end = min(total_lines, e_line)

                repl_text = new_content or ""
                repl_lines = repl_text.splitlines(keepends=True)
                if repl_lines and not repl_lines[-1].endswith(("\n", "\r\n")):
                    newline_char = "\r\n" if "\r\n" in original_text else "\n"
                    repl_lines[-1] += newline_char

                new_file_lines = orig_lines[:slice_start] + repl_lines + orig_lines[slice_end:]
                modified_text = "".join(new_file_lines)
                action_desc = f"Replaced lines {s_line} to {slice_end} ({slice_end - slice_start} lines)"

            else:
                return (
                    "Error: Missing edit parameters. Please specify either:\n"
                    "  1. 'target_content' (and 'replacement_content') for exact string replacement, or\n"
                    "  2. 'start_line' (and optional 'end_line' / 'new_content') for line range replacement."
                )

            if modified_text is None or modified_text == original_text:
                return f"Notice: No modifications were made to '{path}'."

            # Check syntax if python or json
            syntax_warning = self._check_syntax(filepath.suffix, modified_text)

            # Perform atomic write
            atomic_write_text(filepath, modified_text, encoding=encoding)

            # Generate unified diff
            diff = format_unified_diff(
                original_text, modified_text, from_file=f"a/{path}", to_file=f"b/{path}"
            )

            result_parts = [
                f"Successfully updated '{path}' ({action_desc}):",
                f"```diff\n{diff}\n```",
            ]
            if syntax_warning:
                result_parts.append(f"\n{syntax_warning}")

            return "\n".join(result_parts)

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error editing file '%s': %s", path, e, exc_info=True)
            return f"Error editing file '{path}': {e}"

    def _check_syntax(self, ext: str, content: str) -> str | None:
        """Validate syntax of modified file."""
        if ext == ".py":
            try:
                ast.parse(content)
            except SyntaxError as e:
                return f"Syntax Warning: The edit introduced a Python syntax error on line {e.lineno}: {e.msg}"
        elif ext == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return f"Syntax Warning: The edit introduced a JSON syntax error: {e}"
        return None
