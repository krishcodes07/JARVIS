"""
Search Files Tool — Glob and pattern file search across workspace directories.
"""

from __future__ import annotations

import fnmatch
import logging
import os
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)

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
}


class SearchFilesTool(BaseTool):
    """Find files and directories matching a glob pattern or keyword."""

    schema = ToolSchema(
        name="search_files",
        description=(
            "Search for files and directories matching a pattern or glob (e.g. '*.py', 'src/**/*.json', 'test_*'). "
            "Automatically filters out heavy build and cache directories."
        ),
        category="filesystem",
        aliases=["find_files", "glob_search", "find"],
        keywords=["search", "find", "files", "glob", "pattern", "locate", "path"],
        parameters=[
            ToolParameter(
                name="pattern",
                type="string",
                description="Glob pattern or substring to search for (e.g. '*.py', 'test_*.py', 'config').",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Root directory path to start searching from (default: current working directory).",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="type_filter",
                type="string",
                description="Filter results by type: 'all', 'file', or 'dir' (default: 'all').",
                required=False,
                default="all",
                enum=["all", "file", "dir"],
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of results to return (default: 50).",
                required=False,
                default=50,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute file search."""
        pattern = kwargs.get("pattern", "").strip()
        root_path = kwargs.get("path") or "."
        type_filter = kwargs.get("type_filter", "all").lower()
        max_results = int(kwargs.get("max_results") or 50)

        if not pattern:
            return "Error: Pattern parameter is required."

        try:
            base_dir = self.resolve_path(root_path)
            if not base_dir.exists():
                return f"Error: Root directory not found: '{root_path}'"

            # Normalize pattern
            search_pattern = pattern if any(c in pattern for c in "*?[]") else f"*{pattern}*"

            results: list[dict[str, Any]] = []

            for root, dirs, files in os.walk(base_dir):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS and not d.startswith(".")]

                current_root = Path(root)

                # Check directories
                if type_filter in ("all", "dir"):
                    for d in dirs:
                        if fnmatch.fnmatch(d.lower(), search_pattern.lower()):
                            dir_path = current_root / d
                            try:
                                rel = dir_path.relative_to(base_dir)
                            except ValueError:
                                rel = dir_path
                            results.append({"path": str(rel), "type": "DIR", "size": 0})
                            if len(results) >= max_results:
                                break

                if len(results) >= max_results:
                    break

                # Check files
                if type_filter in ("all", "file"):
                    for f in files:
                        if fnmatch.fnmatch(f.lower(), search_pattern.lower()):
                            file_path = current_root / f
                            try:
                                rel = file_path.relative_to(base_dir)
                            except ValueError:
                                rel = file_path
                            try:
                                fsize = file_path.stat().st_size
                            except Exception:
                                fsize = 0
                            results.append({"path": str(rel), "type": "FILE", "size": fsize})
                            if len(results) >= max_results:
                                break

                if len(results) >= max_results:
                    break

            if not results:
                return f"No items found matching pattern '{pattern}' under '{root_path}'."

            truncated = f" (showing first {max_results} results)" if len(results) >= max_results else ""
            lines = [f"Found {len(results)} item(s) matching '{pattern}'{truncated}:\n"]

            for r in results:
                if r["type"] == "DIR":
                    lines.append(f"  [DIR]  {r['path']}/")
                else:
                    lines.append(f"  [FILE] {r['path']} ({r['size']:,} bytes)")

            return "\n".join(lines)

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error searching files with pattern '%s': %s", pattern, e, exc_info=True)
            return f"Error searching files with pattern '{pattern}': {e}"
