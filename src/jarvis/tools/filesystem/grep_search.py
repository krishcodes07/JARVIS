"""
Grep Search Tool — Search file contents for regex or string pattern matching.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def safe_path(path: str) -> str:
    """Resolve file path to an absolute path."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return os.path.realpath(expanded)
    return os.path.realpath(os.path.join(os.getcwd(), expanded))


class GrepSearchTool(BaseTool):
    """Search file contents across a directory using regular expressions or text matching."""

    schema = ToolSchema(
        name="grep_search",
        description="Search text file contents within a directory using regular expressions or keyword matching.",
        category="filesystem",
        aliases=["grep", "search_text", "content_search"],
        keywords=["grep", "search", "content", "regex", "text", "find"],
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
                description="Optional file pattern extension filter (e.g. '*.py' or '*.json').",
                required=False,
            ),
            ToolParameter(
                name="max_matches",
                type="integer",
                description="Maximum line matches to return (default: 50).",
                required=False,
                default=50,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "")
        path = kwargs.get("path") or "."
        file_pattern = kwargs.get("file_pattern")
        max_matches = kwargs.get("max_matches") or 50

        if not query:
            return "Error: Search query parameter is required."

        try:
            target_path = safe_path(path)
            if not os.path.exists(target_path):
                return f"Error: Target path not found: {path}"

            regex = re.compile(query, re.IGNORECASE)
            matches: list[str] = []

            def match_file(filepath: str) -> None:
                if len(matches) >= max_matches:
                    return
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if regex.search(line):
                                rel = os.path.relpath(filepath, os.getcwd())
                                matches.append(f"{rel}:{idx}: {line.strip()}")
                                if len(matches) >= max_matches:
                                    break
                except Exception:
                    pass

            if os.path.isfile(target_path):
                match_file(target_path)
            else:
                for root, _, files in os.walk(target_path):
                    # Skip common heavy dirs
                    if any(ignored in root for ignored in [".git", "__pycache__", ".venv", "node_modules", "data"]):
                        continue
                    for file in files:
                        if file_pattern and not file.endswith(file_pattern.replace("*", "")):
                            continue
                        match_file(os.path.join(root, file))
                        if len(matches) >= max_matches:
                            break
                    if len(matches) >= max_matches:
                        break

            if not matches:
                return f"No matches found for query '{query}' in '{path}'."

            header = f"Found {len(matches)} match(es) for '{query}':\n"
            return header + "\n".join(matches)

        except Exception as e:
            return f"Error performing grep search: {e}"
