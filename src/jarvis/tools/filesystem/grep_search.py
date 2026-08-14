"""
Grep Search Tool — High-performance regex and string pattern search with ripgrep acceleration and context lines.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema, is_binary_file

logger = logging.getLogger(__name__)

# Standard heavy/junk directories to skip automatically
DEFAULT_IGNORED_DIRS: set[str] = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".egg-info",
    "target",
}


class GrepSearchTool(BaseTool):
    """Search file contents within a directory using regular expressions or keyword matching."""

    schema = ToolSchema(
        name="grep_search",
        description=(
            "Search text file contents within a directory or file using regular expressions or literal strings. "
            "Supports ripgrep acceleration, file pattern filtering (e.g. '*.py'), case sensitivity toggle, and context lines."
        ),
        category="filesystem",
        aliases=["grep", "search_text", "content_search", "ripgrep"],
        keywords=["grep", "search", "content", "regex", "text", "find", "code", "pattern"],
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query or regular expression pattern.",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Root directory or file path to search inside (default: current working directory).",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="file_pattern",
                type="string",
                description="Optional glob filter for file names (e.g. '*.py', '*.json', '*.ts').",
                required=False,
            ),
            ToolParameter(
                name="case_sensitive",
                type="boolean",
                description="Whether search should be case sensitive (default: false).",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="max_matches",
                type="integer",
                description="Maximum number of matches to return (default: 50).",
                required=False,
                default=50,
            ),
            ToolParameter(
                name="context_lines",
                type="integer",
                description="Number of context lines to display before and after each match (default: 0).",
                required=False,
                default=0,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute grep search."""
        query = kwargs.get("query", "").strip()
        path = kwargs.get("path") or "."
        file_pattern = kwargs.get("file_pattern")
        case_sensitive = bool(kwargs.get("case_sensitive", False))
        max_matches = int(kwargs.get("max_matches") or 50)
        context_lines = int(kwargs.get("context_lines") or 0)

        if not query:
            return "Error: Search query parameter is required."

        try:
            target_path = self.resolve_path(path)
            if not target_path.exists():
                return f"Error: Target path not found: '{path}'"

            # Try ripgrep first if available on PATH
            if shutil.which("rg") and not context_lines:
                rg_result = self._try_ripgrep(
                    query, target_path, file_pattern, case_sensitive, max_matches
                )
                if rg_result is not None:
                    return rg_result

            # Fallback to pure Python search engine
            return self._python_grep(
                query, target_path, file_pattern, case_sensitive, max_matches, context_lines
            )

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error performing grep search for '%s': %s", query, e, exc_info=True)
            return f"Error performing grep search: {e}"

    def _try_ripgrep(
        self,
        query: str,
        target_path: Path,
        file_pattern: str | None,
        case_sensitive: bool,
        max_matches: int,
    ) -> str | None:
        """Run ripgrep for fast searching."""
        try:
            cmd = ["rg", "--no-heading", "--line-number", "--color", "never", "-m", str(max_matches)]
            if not case_sensitive:
                cmd.append("-i")
            if file_pattern:
                cmd.extend(["-g", file_pattern])

            # Exclude ignored dirs
            for ign in DEFAULT_IGNORED_DIRS:
                cmd.extend(["--glob", f"!{ign}/*"])

            cmd.extend([query, str(target_path)])

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.strip().splitlines()[:max_matches]
                formatted = []
                for line in lines:
                    formatted.append(f"  • {line}")
                return (
                    f"Found {len(formatted)} match(es) for '{query}' in '{target_path.name}':\n"
                    + "\n".join(formatted)
                )
            elif res.returncode == 1:
                return f"No matches found for query '{query}' in '{target_path}'."
        except Exception:
            pass
        return None

    def _python_grep(
        self,
        query: str,
        target_path: Path,
        file_pattern: str | None,
        case_sensitive: bool,
        max_matches: int,
        context_lines: int,
    ) -> str:
        """Pure-Python grep engine with regex and context lines."""
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(query, flags)
        except re.error:
            # Fallback to literal search if regex compilation fails
            regex = re.compile(re.escape(query), flags)

        matches: list[str] = []
        cwd = Path.cwd()

        def search_single_file(fpath: Path) -> None:
            if len(matches) >= max_matches or is_binary_file(fpath):
                return
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for idx, line in enumerate(lines):
                    if regex.search(line):
                        try:
                            rel_path = fpath.relative_to(cwd)
                        except ValueError:
                            rel_path = fpath

                        line_num = idx + 1
                        matched_snippet = line.strip()

                        if context_lines > 0:
                            start_ctx = max(0, idx - context_lines)
                            end_ctx = min(len(lines), idx + context_lines + 1)
                            ctx_block = []
                            for c_idx in range(start_ctx, end_ctx):
                                marker = ">" if c_idx == idx else " "
                                ctx_block.append(f"    {marker} {c_idx + 1:4d}: {lines[c_idx].rstrip()}")
                            matches.append(f"  • {rel_path}:{line_num}:\n" + "\n".join(ctx_block))
                        else:
                            matches.append(f"  • {rel_path}:{line_num}: {matched_snippet}")

                        if len(matches) >= max_matches:
                            break
            except Exception:
                pass

        if target_path.is_file():
            search_single_file(target_path)
        else:
            for root, dirs, files in os.walk(target_path):
                # Filter out heavy directories in-place
                dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS and not d.startswith(".")]

                for file in files:
                    if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                        continue
                    search_single_file(Path(root) / file)
                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break

        if not matches:
            return f"No matches found for query '{query}' in '{target_path}'."

        header = f"Found {len(matches)} match(es) for '{query}':\n"
        return header + "\n".join(matches)
