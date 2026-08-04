"""
Configuration for Terminal MCP server.
"""

import os
import sys
from typing import List

# Default working directory for terminal commands
DEFAULT_CWD = os.environ.get("TERMINAL_DEFAULT_CWD", os.getcwd())
# Default command execution timeout in seconds
DEFAULT_TIMEOUT = int(os.environ.get("TERMINAL_TIMEOUT", "60"))


def resolve_cwd(cwd: str | None = None) -> str:
    """Resolve working directory for terminal commands."""
    if not cwd:
        return os.getcwd()
    expanded = os.path.expanduser(cwd)
    if os.path.isabs(expanded):
        return os.path.realpath(expanded)
    return os.path.realpath(os.path.join(os.getcwd(), expanded))


def validate() -> List[str]:
    """Validate terminal configuration."""
    return []
