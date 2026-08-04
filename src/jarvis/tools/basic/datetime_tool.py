"""
DateTime Tool — Date and time operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class DateTimeTool(BaseTool):
    """Get current date/time or perform date calculations."""

    schema = ToolSchema(
        name="datetime",
        description="Get the current date and time, or perform date/time calculations.",
        category="basic",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action: 'now' for current time, 'format' to format a date",
                required=False,
                default="now",
            ),
            ToolParameter(
                name="timezone",
                type="string",
                description="Timezone (e.g., 'UTC', 'US/Eastern')",
                required=False,
                default="UTC",
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Get current date/time."""
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
