"""
Copy File Tool — Copy files or directories to a destination path.
"""

from __future__ import annotations

import logging
import shutil
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class CopyFileTool(BaseTool):
    """Copy a file or directory tree to a new destination."""

    schema = ToolSchema(
        name="copy_file",
        description="Copy a file or directory tree to a specified destination path.",
        category="filesystem",
        aliases=["cp", "copy", "duplicate"],
        keywords=["copy", "cp", "duplicate", "file", "folder", "clone"],
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
        """Execute copy operation."""
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

            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                return f"Successfully copied directory '{src}' to '{dst}'."
            else:
                shutil.copy2(src_path, dst_path)
                return f"Successfully copied file '{src}' to '{dst}' ({src_path.stat().st_size:,} bytes)."

        except PermissionError as e:
            return f"Permission Denied: {e}"
        except Exception as e:
            logger.error("Error copying '%s' to '%s': %s", src, dst, e, exc_info=True)
            return f"Error copying '{src}' to '{dst}': {e}"
