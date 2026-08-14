"""
Web Search Tool — Search the web using DuckDuckGo with zero API keys required.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any
from urllib.parse import quote_plus, unquote

import httpx

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web for up-to-date information, documentation, and answers."""

    schema = ToolSchema(
        name="web_search",
        description=(
            "Search the public web for real-time information, programming documentation, news, or answers. "
            "Returns top search results with titles, links, and text snippets."
        ),
        category="basic",
        aliases=["search_web", "google", "ddg", "duckduckgo", "web"],
        keywords=["search", "web", "google", "internet", "query", "lookup", "documentation", "online"],
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query string.",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of search results to return (default: 5).",
                required=False,
                default=5,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute web search using DuckDuckGo."""
        query = kwargs.get("query", "").strip()
        max_results = int(kwargs.get("max_results") or 5)

        if not query:
            return "Error: Search query is required."

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            # 1. DuckDuckGo HTML Lite search
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    # Fallback to standard html search endpoint
                    url_fb = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                    resp = await client.get(url_fb, headers=headers)

            if resp.status_code != 200:
                return f"Web search request failed with HTTP status {resp.status_code}."

            results = self._parse_ddg_html(resp.text, max_results)

            if not results:
                return f"No web search results found for query: '{query}'."

            output_lines = [f"Web Search Results for '{query}':\n"]
            for idx, r in enumerate(results, start=1):
                output_lines.append(f"### {idx}. {r['title']}")
                output_lines.append(f"URL: {r['url']}")
                output_lines.append(f"Snippet: {r['snippet']}\n")

            return "\n".join(output_lines)

        except httpx.TimeoutException:
            return f"Error: Web search timed out while querying '{query}'."
        except Exception as e:
            logger.error("Web search error for query '%s': %s", query, e, exc_info=True)
            return f"Error performing web search: {e}"

    def _parse_ddg_html(self, html_text: str, max_results: int) -> list[dict[str, str]]:
        """Parse DuckDuckGo HTML result page into structured results."""
        results: list[dict[str, str]] = []

        # Find result snippets in DuckDuckGo HTML
        # Pattern for standard DuckDuckGo HTML result blocks
        # <a class="result__snippet" ...>snippet</a>
        # <a class="result__url" href="...">url</a>
        # <a class="result__a" href="...">title</a>

        result_blocks = re.findall(
            r'<div class="[^"]*result__body[^"]*">(.*?)</div>\s*</div>',
            html_text,
            re.DOTALL | re.IGNORECASE,
        )

        for block in result_blocks:
            if len(results) >= max_results:
                break

            # Title and URL
            title_match = re.search(
                r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE,
            )
            snippet_match = re.search(
                r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE,
            )

            if title_match:
                raw_url = title_match.group(1)
                raw_title = title_match.group(2)
                raw_snippet = snippet_match.group(1) if snippet_match else ""

                # Decode DuckDuckGo redirect URL
                actual_url = raw_url
                if "uddg=" in raw_url:
                    m = re.search(r"uddg=([^&]+)", raw_url)
                    if m:
                        actual_url = unquote(m.group(1))

                clean_title = self._clean_html(raw_title)
                clean_snippet = self._clean_html(raw_snippet)

                if clean_title and actual_url:
                    results.append({
                        "title": clean_title,
                        "url": actual_url,
                        "snippet": clean_snippet or "[No snippet available]",
                    })

        # Fallback table parser for lite.duckduckgo.com
        if not results:
            lite_links = re.findall(
                r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<td class="result-snippet">(.*?)</td>',
                html_text,
                re.DOTALL | re.IGNORECASE,
            )
            for raw_url, raw_title, raw_snippet in lite_links:
                if len(results) >= max_results:
                    break
                actual_url = unquote(raw_url) if "uddg=" in raw_url else raw_url
                results.append({
                    "title": self._clean_html(raw_title),
                    "url": actual_url,
                    "snippet": self._clean_html(raw_snippet),
                })

        return results

    def _clean_html(self, raw_html: str) -> str:
        """Strip HTML tags and unescape HTML entities."""
        text = re.sub(r"<[^<]+?>", "", raw_html)
        text = html.unescape(text)
        return " ".join(text.split()).strip()
