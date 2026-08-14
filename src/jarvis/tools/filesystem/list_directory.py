"""
List Directory Tool — Hierarchical directory listing with metadata, depth control, and formatting.
"""

from __future__ import annotations

import logging
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
}


class ListDirectoryTool(BaseTool):
    """List directory contents with hierarchical tree support, sizes, and file counts."""

    schema = ToolSchema(
        name="list_directory",
        description=(
            "List files and subdirectories inside a directory path with file sizes and item counts. "
            "Supports multi-level depth inspection (e.g. max_depth=2 for tree view)."
        ),
        category="filesystem",
        aliases=["ls", "dir", "list_dir", "tree"],
        keywords=["list", "directory", "folder", "ls", "dir", "files", "tree"],
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Directory path to list (default: current working directory).",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="max_depth",
                type="integer",
                description="Maximum directory traversal depth (default: 1 for immediate children).",
                required=False,
                default=1,
            ),
            ToolParameter(
                name="show_all",
                type="boolean",
                description="Whether to include hidden and cache folders like .git, __pycache__ (default: false).",
                required=False,
                default=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute directory listing."""
        path = kwargs.get("path") or "."
        max_depth = max(1, int(kwargs.get("max_depth") or 1))
        show_all = bool(kwargs.get("show_all", False))

        try:
            dirpath = self.resolve_path(path)
            if not dirpath.exists():
                return f"Error: Directory not found: '{path}'"
            if not dirpath.is_dir():
                return f"Error: Path is a file, not a directory: '{path}'"

            lines: list[str] = [f"Directory contents of '{path}':\n"]
            total_items = self._build_tree(dirpath, dirpath, 1, max_depth, show_all, lines, "")

            if total_items == 0:
                return f"Directory '{path}' is empty."

            return "\n".join(lines)

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error listing directory '%s': %s", path, e, exc_info=True)
            return f"Error listing directory '{path}': {e}"

    def _build_tree(
        self,
        base_dir: Path,
        current_dir: Path,
        current_depth: int,
        max_depth: int,
        show_all: bool,
        lines: list[str],
        indent: str,
    ) -> int:
        """Recursively build formatted directory listing."""
        try:
            entries = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception as e:
            lines.append(f"{indent}[Permission/Access Error: {e}]")
            return 0

        # Filter entries
        visible_entries = []
        for entry in entries:
            if not show_all:
                if entry.name in DEFAULT_IGNORED_DIRS or (entry.name.startswith(".") and entry.name != ".env"):
                    continue
            visible_entries.append(entry)

        count = len(visible_entries)
        for idx, entry in enumerate(visible_entries):
            is_last = idx == (count - 1)
            prefix = "└── " if is_last else "├── "
            next_indent = indent + ("    " if is_last else "│   ")

            if entry.is_dir():
                try:
                    child_count = len([c for c in entry.iterdir() if show_all or not c.name.startswith(".")])
                    lines.append(f"{indent}{prefix}[DIR]  {entry.name}/ ({child_count} items)")
                except Exception:
                    lines.append(f"{indent}{prefix}[DIR]  {entry.name}/")

                if current_depth < max_depth:
                    self._build_tree(base_dir, entry, current_depth + 1, max_depth, show_all, lines, next_indent)
            else:
                try:
                    size = entry.stat().st_size
                    lines.append(f"{indent}{prefix}[FILE] {entry.name} ({size:,} bytes)")
                except Exception:
                    lines.append(f"{indent}{prefix}[FILE] {entry.name}")

        return count
