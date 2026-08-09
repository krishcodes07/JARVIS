"""
Delete File Tool — Delete a file or directory.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def safe_path(path: str) -> str:
    """Resolve file path to an absolute path."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return os.path.realpath(expanded)
    return os.path.realpath(os.path.join(os.getcwd(), expanded))


class DeleteFileTool(BaseTool):
    """Delete a file or recursively remove a directory."""

    schema = ToolSchema(
        name="delete_file",
        description="Delete a file or recursively remove a directory folder.",
        category="filesystem",
        aliases=["rm", "unlink", "remove_file", "delete_folder"],
        keywords=["delete", "remove", "unlink", "rm", "file", "folder"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Path of file or directory to delete.",
                required=True,
            ),
            ToolParameter(
                name="recursive",
                type="boolean",
                description="Set to true if deleting a directory.",
                required=False,
                default=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        recursive = kwargs.get("recursive", False)

        if not path:
            return "Error: Path is required."

        try:
            target = self.resolve_path(path)
            if not target.exists():
                return f"Error: Path not found: {path}"

            if target.is_dir():
                if not recursive:
                    return f"Error: '{path}' is a directory. Set recursive=True to delete directory."
                shutil.rmtree(target)
                return f"Successfully deleted directory '{path}'."
            else:
                target.unlink()
                return f"Successfully deleted file '{path}'."

        except Exception as e:
            return f"Error deleting '{path}': {e}"
