"""
Grep search tool for Filesystem — search inside file contents.
"""

import fnmatch
import os
import re
from typing import Optional
from ..config import safe_path

NAME = "grep_search"
DESCRIPTION = "Search for text or regex patterns inside files across a directory tree."


def grep_search(
    query: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = 50,
    is_regex: bool = False,
    encoding: str = "utf-8",
) -> str:
    """
    Search inside files for text or regex query.

    Args:
        query: Text or regex query to match in file contents.
        path: Directory to search (default: current directory).
        file_pattern: Filename wildcard pattern to include (default: *).
        max_results: Max matching lines to return (default: 50).
        is_regex: If True, treat query as a regular expression.
        encoding: File encoding (default: utf-8).

    Returns:
        Formatted list of matching file lines and numbers.
    """
    try:
        dirpath = safe_path(path)
        if not os.path.exists(dirpath):
            return f"Error: Path not found: {path}"

        if is_regex:
            pattern_re = re.compile(query, re.IGNORECASE)
        else:
            query_lower = query.lower()

        results = []
        match_count = 0

        for root, dirs, files in os.walk(dirpath):
            # Skip hidden folders and venvs
            dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d not in ("node_modules", "venv", ".venv")]

            for filename in files:
                if not fnmatch.fnmatch(filename.lower(), file_pattern.lower()):
                    continue

                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, dirpath)

                try:
                    with open(full_path, "r", encoding=encoding, errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            matched = False
                            if is_regex:
                                matched = bool(pattern_re.search(line))
                            else:
                                matched = query_lower in line.lower()

                            if matched:
                                snippet = line.strip()
                                if len(snippet) > 150:
                                    snippet = snippet[:150] + "..."
                                results.append(f"  📄 {rel_path}:{line_num} | {snippet}")
                                match_count += 1
                                if match_count >= max_results:
                                    break
                except Exception:
                    continue

                if match_count >= max_results:
                    break
            if match_count >= max_results:
                break

        if not results:
            return f"Search: No content matches found for '{query}' in '{path}'."

        header = f"Search Results for '{query}' ({match_count} matches):\n"
        return header + "\n".join(results)

    except Exception as e:
        return f"Error: Failed grep search: {e}"
