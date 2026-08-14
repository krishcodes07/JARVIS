"""
Move File Tool — Move or rename files and directories.
"""

from __future__ import annotations

import logging
import shutil
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class MoveFileTool(BaseTool):
    """Move or rename a file or directory to a destination path."""

    schema = ToolSchema(
        name="move_file",
        description="Move or rename a file or directory to a destination path.",
        category="filesystem",
        aliases=["mv", "rename", "move"],
        keywords=["move", "rename", "mv", "file", "folder", "relocate"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="source",
                type="string",
                description="Source file or directory path.",
                required=True,
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Destination file or directory path.",
                required=True,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute move/rename operation."""
        src = kwargs.get("source", "").strip()
        dst = kwargs.get("destination", "").strip()

        if not src or not dst:
            return "Error: Both 'source' and 'destination' paths are required."

        try:
            src_path = self.resolve_path(src)
            dst_path = self.resolve_path(dst)

            if not src_path.exists():
                return f"Error: Source path not found: '{src}'"

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return f"Successfully moved/renamed '{src}' to '{dst}'."

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error moving '%s' to '%s': %s", src, dst, e, exc_info=True)
            return f"Error moving '{src}' to '{dst}': {e}"
