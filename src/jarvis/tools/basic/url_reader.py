"""
URL Reader Tool — Fetch and extract content from URLs.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class URLReaderTool(BaseTool):
    """Fetch and read content from a URL."""

    schema = ToolSchema(
        name="url_reader",
        description="Fetch the content of a web page and return it as text. Useful for reading documentation, articles, and web content.",
        category="basic",
        parameters=[
            ToolParameter(name="url", type="string", description="The URL to fetch"),
            ToolParameter(name="max_length", type="integer", description="Maximum content length to return", required=False, default=5000),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Fetch URL content."""
        url = kwargs["url"]
        max_length = kwargs.get("max_length", 5000)

        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text[:max_length]
                return f"Content from {url}:\n\n{text}"
        except Exception as e:
            return f"Error fetching {url}: {e}"
