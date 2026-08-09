"""
Move File Tool — Move or rename files and directories.
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


class MoveFileTool(BaseTool):
    """Move or rename a file or directory to a destination path."""

    schema = ToolSchema(
        name="move_file",
        description="Move or rename a file or directory to a destination path.",
        category="filesystem",
        aliases=["mv", "rename", "move"],
        keywords=["move", "rename", "mv", "file", "folder"],
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
        src = kwargs.get("source", "")
        dst = kwargs.get("destination", "")

        if not src or not dst:
            return "Error: Both 'source' and 'destination' paths are required."

        try:
            src_path = self.resolve_path(src)
            dst_path = self.resolve_path(dst)

            if not src_path.exists():
                return f"Error: Source path not found: {src}"

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return f"Successfully moved/renamed '{src}' to '{dst}'."

        except Exception as e:
            return f"Error moving '{src}' to '{dst}': {e}"
