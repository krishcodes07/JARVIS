"""
Delete File Tool — Delete a file or directory with safety checks.
"""

from __future__ import annotations

import logging
import shutil
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class DeleteFileTool(BaseTool):
    """Delete a file or recursively remove a directory folder."""

    schema = ToolSchema(
        name="delete_file",
        description="Delete a file or recursively remove a directory folder.",
        category="filesystem",
        aliases=["rm", "unlink", "remove_file", "delete_folder"],
        keywords=["delete", "remove", "unlink", "rm", "file", "folder", "trash"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Path of the file or directory to delete.",
                required=True,
            ),
            ToolParameter(
                name="recursive",
                type="boolean",
                description="Set to true if deleting a non-empty directory (default: false).",
                required=False,
                default=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute delete operation."""
        path = kwargs.get("path", "").strip()
        recursive = bool(kwargs.get("recursive", False))

        if not path:
            return "Error: Path is required."

        try:
            target = self.resolve_path(path)
            if not target.exists():
                return f"Error: Target path not found: '{path}'"

            if target.is_dir():
                if not recursive:
                    return f"Error: '{path}' is a directory. Set 'recursive=True' to confirm directory deletion."
                shutil.rmtree(target)
                return f"Successfully deleted directory '{path}'."
            else:
                target.unlink()
                return f"Successfully deleted file '{path}'."

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error deleting '%s': %s", path, e, exc_info=True)
            return f"Error deleting '{path}': {e}"
