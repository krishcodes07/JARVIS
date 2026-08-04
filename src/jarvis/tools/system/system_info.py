"""
System Info Tool — Get system information.
"""

from __future__ import annotations

import logging
import platform
import sys
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    """Get information about the current system."""

    schema = ToolSchema(
        name="system_info",
        description="Get system information: OS, CPU, memory, Python version, etc.",
        category="system",
        parameters=[],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Get system info."""
        info = {
            "OS": f"{platform.system()} {platform.release()}",
            "Architecture": platform.machine(),
            "Python": sys.version,
            "Platform": platform.platform(),
            "Hostname": platform.node(),
        }

        lines = [f"  {k}: {v}" for k, v in info.items()]
        return "System Information:\n" + "\n".join(lines)
