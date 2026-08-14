"""
Read URL Tool — Fetch and convert web pages to clean Markdown text for LLM consumption.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any

import httpx

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class ReadUrlTool(BaseTool):
    """Fetch content from a web URL and extract clean, readable Markdown text."""

    schema = ToolSchema(
        name="read_url",
        description=(
            "Fetch the text content of a web page URL and convert it into clean Markdown. "
            "Removes noise (scripts, styles, navigation, ads) and extracts headings, paragraphs, and links."
        ),
        category="basic",
        aliases=["fetch_url", "web_page", "get_url", "browse_url"],
        keywords=["url", "web", "fetch", "http", "html", "page", "scrape", "browse", "documentation"],
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="The full HTTP or HTTPS URL to fetch.",
                required=True,
            ),
            ToolParameter(
                name="max_chars",
                type="integer",
                description="Maximum number of characters to return (default: 30,000).",
                required=False,
                default=30_000,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Fetch and parse web page."""
        url = kwargs.get("url", "").strip()
        max_chars = int(kwargs.get("max_chars") or 30_000)

        if not url:
            return "Error: URL is required."

        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)

            if resp.status_code != 200:
                return f"Error: Request to '{url}' failed with HTTP status {resp.status_code} ({resp.reason_phrase})."

            content_type = resp.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                return f"JSON Response from {url}:\n```json\n{resp.text[:max_chars]}\n```"
            elif "text/plain" in content_type:
                text = resp.text
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n[Truncated at {max_chars:,} chars]"
                return f"Plain Text from {url}:\n\n{text}"

            markdown_text, page_title = self._html_to_markdown(resp.text)

            truncated_notice = ""
            if len(markdown_text) > max_chars:
                markdown_text = markdown_text[:max_chars]
                truncated_notice = f" [Truncated at {max_chars:,} chars]"

            header = (
                f"Web Page Content: {page_title or url}\n"
                f"URL: {url} | Status: {resp.status_code}{truncated_notice}\n"
                f"{'=' * 60}\n\n"
            )

            return header + markdown_text

        except httpx.TimeoutException:
            return f"Error: Request to '{url}' timed out."
        except Exception as e:
            logger.error("Error reading URL '%s': %s", url, e, exc_info=True)
            return f"Error reading URL '{url}': {e}"

    def _html_to_markdown(self, raw_html: str) -> tuple[str, str]:
        """Convert HTML to clean structured Markdown."""
        # 1. Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.DOTALL | re.IGNORECASE)
        page_title = html.unescape(title_match.group(1)).strip() if title_match else ""

        # 2. Strip noisy elements
        cleaned = re.sub(r"<(script|style|nav|header|footer|aside|svg|noscript)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)

        # 3. Convert headers
        for h in range(6, 0, -1):
            cleaned = re.sub(
                rf"<h{h}[^>]*>(.*?)</h{h}>",
                rf"\n\n{'#' * h} \1\n\n",
                cleaned,
                flags=re.DOTALL | re.IGNORECASE,
            )

        # 4. Convert paragraphs & breaks
        cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\n\1\n\n", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<hr\s*/?>", "\n---\n", cleaned, flags=re.IGNORECASE)

        # 5. Convert list items
        cleaned = re.sub(r"<li[^>]*>(.*?)</li>", r"\n* \1", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 6. Convert bold & italic
        cleaned = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 7. Strip remaining HTML tags
        text = re.sub(r"<[^<]+?>", "", cleaned)
        text = html.unescape(text)

        # 8. Normalize whitespace and newlines
        lines = [line.strip() for line in text.splitlines()]
        # Remove consecutive blank lines
        result_lines = []
        blank = False
        for line in lines:
            if line:
                result_lines.append(line)
                blank = False
            elif not blank:
                result_lines.append("")
                blank = True

        return "\n".join(result_lines).strip(), page_title
