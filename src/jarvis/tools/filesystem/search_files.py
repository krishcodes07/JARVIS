"""
Search Files Tool — Search for files matching pattern or glob.
"""

from __future__ import annotations

import glob
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


class SearchFilesTool(BaseTool):
    """Find files and directories matching a glob pattern."""

    schema = ToolSchema(
        name="search_files",
        description="Search for files and directories matching a glob pattern (e.g. '*.py', 'src/**/*.json').",
        category="filesystem",
        aliases=["find_files", "glob_search"],
        keywords=["search", "find", "files", "glob", "pattern"],
        parameters=[
            ToolParameter(
                name="pattern",
                type="string",
                description="Glob pattern to search for (e.g. '*.py' or 'src/**/*.py').",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Root directory path to start search from (default: current working directory).",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of file results to return (default: 50).",
                required=False,
                default=50,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        pattern = kwargs.get("pattern", "")
        root_path = kwargs.get("path") or "."
        max_results = kwargs.get("max_results") or 50

        if not pattern:
            return "Error: Pattern parameter is required."

        try:
            base_dir = safe_path(root_path)
            if not os.path.exists(base_dir):
                return f"Error: Root directory not found: {root_path}"

            search_glob = os.path.join(base_dir, pattern)
            matches = glob.glob(search_glob, recursive=True)

            if not matches:
                return f"No files found matching pattern '{pattern}' under '{root_path}'."

            rel_matches = [os.path.relpath(m, base_dir) for m in matches[:max_results]]
            truncated = f" (showing first {max_results} results)" if len(matches) > max_results else ""

            lines = [f"Found {len(matches)} item(s) matching '{pattern}'{truncated}:\n"]
            for m in rel_matches:
                lines.append(f"  • {m}")

            return "\n".join(lines)

        except Exception as e:
            return f"Error searching files with pattern '{pattern}': {e}"
