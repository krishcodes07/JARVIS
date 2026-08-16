"""
Web Search Tool — Multi-engine web search with zero API keys required.

Uses DDGS (DuckDuckGo Search) as the primary backend with an automatic
fallback to Bing Search (and DuckDuckGo HTML) to guarantee search availability
and prevent HTTP 202 / bot-blocking failures.
"""

from __future__ import annotations

import asyncio
import base64
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
        aliases=["search_web", "google", "ddg", "duckduckgo", "web", "bing"],
        keywords=["search", "web", "google", "bing", "internet", "query", "lookup", "documentation", "online"],
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
        """Execute web search across backends with seamless fallbacks."""
        query = kwargs.get("query", "").strip()
        max_results = int(kwargs.get("max_results") or 5)

        if not query:
            return "Error: Search query is required."

        results: list[dict[str, str]] = []

        # 1. Primary Engine: ddgs / duckduckgo_search library
        try:
            results = await self._search_ddgs(query, max_results)
        except Exception as e:
            logger.debug(f"DDGS search failed for '{query}': {e}")

        # 2. Fallback Engine 1: Bing HTML Search
        if not results:
            try:
                results = await self._search_bing(query, max_results)
            except Exception as e:
                logger.debug(f"Bing search fallback failed for '{query}': {e}")

        # 3. Fallback Engine 2: DuckDuckGo HTML Direct
        if not results:
            try:
                results = await self._search_ddg_html(query, max_results)
            except Exception as e:
                logger.debug(f"DDG HTML search fallback failed for '{query}': {e}")

        if not results:
            return f"No web search results found for query: '{query}'."

        output_lines = [f"Web Search Results for '{query}':\n"]
        for idx, r in enumerate(results[:max_results], start=1):
            output_lines.append(f"### {idx}. {r['title']}")
            output_lines.append(f"URL: {r['url']}")
            output_lines.append(f"Snippet: {r['snippet']}\n")

        return "\n".join(output_lines)

    async def _search_ddgs(self, query: str, max_results: int) -> list[dict[str, str]]:
        """Query DuckDuckGo using the ddgs library in a worker thread."""
        def _sync_ddgs_call() -> list[dict[str, str]]:
            try:
                try:
                    from ddgs import DDGS  # type: ignore
                except ImportError:
                    from duckduckgo_search import DDGS  # type: ignore

                raw = list(DDGS().text(query, max_results=max_results))
                parsed: list[dict[str, str]] = []
                for item in raw:
                    title = item.get("title", "").strip()
                    url = item.get("href", "").strip()
                    snippet = item.get("body", "").strip()
                    if title and url:
                        parsed.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet or "[No snippet available]",
                        })
                return parsed
            except Exception as ex:
                logger.debug(f"ddgs invocation error: {ex}")
                return []

        return await asyncio.to_thread(_sync_ddgs_call)

    async def _search_bing(self, query: str, max_results: int) -> list[dict[str, str]]:
        """Scrape Bing HTML search with base64 redirect URL unmasking."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []

            results: list[dict[str, str]] = []
            blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', resp.text, re.DOTALL)
            for b in blocks:
                if len(results) >= max_results:
                    break

                m_link = re.search(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', b, re.DOTALL)
                m_snip = re.search(r'<p[^>]*>(.*?)</p>', b, re.DOTALL)
                if m_link:
                    raw_url = m_link.group(1)
                    title = self._clean_html(m_link.group(2))
                    snippet = self._clean_html(m_snip.group(1)) if m_snip else "[No snippet available]"
                    actual_url = self._decode_bing_url(raw_url)

                    if title and actual_url:
                        results.append({
                            "title": title,
                            "url": actual_url,
                            "snippet": snippet,
                        })

            return results

    async def _search_ddg_html(self, query: str, max_results: int) -> list[dict[str, str]]:
        """DuckDuckGo HTML Lite fallback."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                url_fb = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                resp = await client.get(url_fb, headers=headers)

            if resp.status_code != 200:
                return []

            results: list[dict[str, str]] = []
            result_blocks = re.findall(
                r'<div class="[^"]*result__body[^"]*">(.*?)</div>\s*</div>',
                resp.text,
                re.DOTALL | re.IGNORECASE,
            )

            for block in result_blocks:
                if len(results) >= max_results:
                    break

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

            return results

    def _decode_bing_url(self, url: str) -> str:
        """Decode base64 encoded destination URL from Bing redirect."""
        m = re.search(r"[?&]u=a1([A-Za-z0-9_-]+)", url)
        if m:
            b64 = m.group(1).replace("-", "+").replace("_", "/")
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            try:
                return base64.b64decode(padded).decode("utf-8", errors="ignore")
            except Exception:
                pass
        return url

    def _clean_html(self, raw_html: str) -> str:
        """Strip HTML tags and unescape HTML entities."""
        text = re.sub(r"<[^<]+?>", "", raw_html)
        text = html.unescape(text)
        return " ".join(text.split()).strip()
