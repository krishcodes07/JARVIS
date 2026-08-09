"""
Make Directory Tool — Create new directories.
"""

from __future__ import annotations

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


class MakeDirectoryTool(BaseTool):
    """Create a new directory including any missing parent directories."""

    schema = ToolSchema(
        name="make_directory",
        description="Create a directory path (mkdir -p). Creates missing parent directories automatically.",
        category="filesystem",
        aliases=["mkdir", "create_directory", "create_folder"],
        keywords=["make", "mkdir", "create", "directory", "folder"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Directory path to create.",
                required=True,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        if not path:
            return "Error: Directory path is required."

        try:
            dirpath = self.resolve_path(path)
            dirpath.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory '{path}'."
        except Exception as e:
            return f"Error creating directory '{path}': {e}"
