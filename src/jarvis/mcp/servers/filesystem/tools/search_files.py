"""
Search files tool for Filesystem.
"""

import fnmatch
import os
from ..config import safe_path

NAME = "search_files"
DESCRIPTION = "Search for files by name pattern within the allowed directory."


def search_files(pattern: str, path: str = ".", max_results: int = 20) -> str:
    """
    Search for files by name pattern (supports wildcards like *.txt, report*).

    Args:
        pattern: File name pattern with wildcards (e.g., '*.py', 'report*').
        path: Directory to search in (default: root).
        max_results: Maximum number of results (default: 20).

    Returns:
        List of matching file paths.
    """
    try:
        dirpath = safe_path(path)
        matches = []

        for root, dirs, files in os.walk(dirpath):
            for filename in files:
                if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                    rel_path = os.path.relpath(os.path.join(root, filename), dirpath)
                    matches.append(rel_path)
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break

        if not matches:
            return f"🔍 No files found matching '{pattern}' in '{path}'."

        return f"🔍 Found {len(matches)} files matching '{pattern}':\n" + "\n".join(
            f"  📄 {m}" for m in matches
        )

    except PermissionError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Error searching: {e}"
