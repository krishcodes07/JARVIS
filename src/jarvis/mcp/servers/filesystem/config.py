"""
Configuration and safety resolution for Filesystem MCP server.
"""

import os
from typing import List

ALLOWED_DIR = os.environ.get("FS_ALLOWED_DIR", "").strip()


def safe_path(path: str) -> str:
    """
    Resolve path.
    - If path is absolute (e.g. D:/Coding or C:/Users), use absolute path directly.
    - If path is relative, resolve relative to current working directory (or ALLOWED_DIR if explicitly restricted).
    """
    expanded = os.path.expanduser(path)

    if os.path.isabs(expanded):
        resolved = os.path.realpath(expanded)
    else:
        base_dir = ALLOWED_DIR if (ALLOWED_DIR and ALLOWED_DIR not in ("*", "ALL")) else os.getcwd()
        resolved = os.path.realpath(os.path.join(base_dir, expanded))

    # Boundary check ONLY if FS_ALLOWED_DIR is explicitly configured to a specific path
    if ALLOWED_DIR and ALLOWED_DIR not in ("*", "ALL", "") and not os.path.isabs(expanded):
        allowed_real = os.path.realpath(ALLOWED_DIR)
        if not resolved.startswith(allowed_real):
            raise PermissionError(
                f"Access denied: path '{path}' is outside the allowed directory '{ALLOWED_DIR}'"
            )

    return resolved


def validate() -> List[str]:
    """Validate Filesystem server configuration."""
    errors = []
    if ALLOWED_DIR and ALLOWED_DIR not in ("*", "ALL", ""):
        if not os.path.exists(ALLOWED_DIR):
            try:
                os.makedirs(ALLOWED_DIR, exist_ok=True)
            except Exception as e:
                errors.append(f"FS_ALLOWED_DIR '{ALLOWED_DIR}' does not exist and cannot be created: {e}")
    return errors
