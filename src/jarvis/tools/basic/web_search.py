"""
Web Search Tool — Multi-engine web search with zero API keys required.

Uses DDGS (DuckDuckGo Search) as the primary backend with an automatic
fallback to Bing Search (and DuckDuckGo HTML) to guarantee search availability
and prevent HTTP 202 / bot-blocking failures.

Optionally (fetch_content=True) also crawls every result URL CONCURRENTLY
and extracts only the main/article content of each page (navbars, footers,
ads, and other boilerplate are stripped out via trafilatura). Fetching is
built for speed:
    - asyncio + httpx.AsyncClient (HTTP/2, pooled connections) so all pages
      download in parallel instead of one after another.
    - A semaphore caps concurrency so we don't get rate-limited/blocked.
    - Content extraction (CPU-bound) runs in a thread pool via
      asyncio.to_thread so it never blocks other in-flight downloads.
    - Per-request timeouts + one retry with backoff so a single slow or
      flaky page can't stall the whole batch.
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
import trafilatura

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Shared fetch config (used by content-fetching layer below)
# --------------------------------------------------------------------------
FETCH_TIMEOUT = 10.0            # seconds, per-request network timeout
MAX_CONCURRENT_FETCHES = 10     # cap on simultaneous page downloads
MAX_FETCH_RETRIES = 1           # extra attempt for pages that fail

# A fuller, more "real browser" header set. Some sites (AccuWeather, etc.)
# check more than just User-Agent, so Accept/Accept-Language/Sec-Fetch-*
# headers meaningfully improve success rate. This still won't beat sites
# with heavy JS-challenge bot protection (Cloudflare JS challenge, etc.) --
# those need a real browser (e.g. Playwright), which trades away speed.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}


class WebSearchTool(BaseTool):
    """Search the web for up-to-date information, documentation, and answers."""

    schema = ToolSchema(
        name="web_search",
        description=(
            "Search the public web for real-time information, programming documentation, news, or answers. "
            "Returns top search results with titles, links, and text snippets. "
            "Optionally fetches and returns the main article content of each result page."
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
            ToolParameter(
                name="fetch_content",
                type="boolean",
                description=(
                    "If true, crawl every result URL in parallel and extract the main "
                    "page content (article text, stripped of navs/footers/ads). "
                    "Slower than a plain search but returns full page content, not just snippets. "
                    "Default: false."
                ),
                required=False,
                default=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute web search across backends with seamless fallbacks."""
        query = kwargs.get("query", "").strip()
        max_results = int(kwargs.get("max_results") or 5)
        fetch_content = bool(kwargs.get("fetch_content") or False)

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

        results = results[:max_results]

        # 4. Optional: crawl all result URLs in parallel and extract main content
        if fetch_content:
            try:
                results = await self._fetch_all_content(results)
            except Exception as e:
                logger.debug(f"Parallel content fetch failed for '{query}': {e}")

        output_lines = [f"Web Search Results for '{query}':\n"]
        for idx, r in enumerate(results, start=1):
            output_lines.append(f"### {idx}. {r['title']}")
            output_lines.append(f"URL: {r['url']}")
            output_lines.append(f"Snippet: {r['snippet']}")
            if fetch_content:
                content = r.get("content")
                if content:
                    output_lines.append(f"Main Content:\n{content}")
                else:
                    output_lines.append(f"Main Content: [unavailable — {r.get('content_error', 'unknown error')}]")
            output_lines.append("")

        return "\n".join(output_lines)

    # ----------------------------------------------------------------
    # Search backends
    # ----------------------------------------------------------------
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
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=BROWSER_HEADERS)
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
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=BROWSER_HEADERS)
            if resp.status_code != 200:
                url_fb = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                resp = await client.get(url_fb, headers=BROWSER_HEADERS)

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

    # ----------------------------------------------------------------
    # Parallel content fetching + main-content extraction
    # ----------------------------------------------------------------
    async def _fetch_all_content(self, results: list[dict[str, str]]) -> list[dict[str, str]]:
        """Crawl every result URL concurrently and attach extracted main content."""
        sem = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
        limits = httpx.Limits(
            max_connections=MAX_CONCURRENT_FETCHES,
            max_keepalive_connections=MAX_CONCURRENT_FETCHES,
        )

        async with httpx.AsyncClient(headers=BROWSER_HEADERS, limits=limits, http2=True) as client:
            tasks = [self._fetch_one_content(client, sem, r) for r in results]
            return await asyncio.gather(*tasks)

    async def _fetch_one_content(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        result: dict[str, str],
    ) -> dict[str, str]:
        """Fetch a single URL and extract its main content. Mutates & returns result."""
        url = result.get("url", "")
        if not url:
            result["content"] = ""
            result["content_error"] = "No URL"
            return result

        async with sem:
            page_html = None
            last_error: Exception | None = None
            for attempt in range(MAX_FETCH_RETRIES + 1):
                try:
                    resp = await client.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
                    resp.raise_for_status()
                    page_html = resp.text
                    break
                except Exception as e:
                    last_error = e
                    if attempt < MAX_FETCH_RETRIES:
                        await asyncio.sleep(0.5 * (attempt + 1))
            if page_html is None:
                result["content"] = ""
                result["content_error"] = f"Fetch failed: {last_error}"
                return result

        # trafilatura strips nav/footer/ads/sidebars and keeps the main
        # article text. Runs in a thread so it never blocks other
        # downloads still in flight.
        try:
            extracted = await asyncio.to_thread(
                trafilatura.extract,
                page_html,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
            result["content"] = extracted.strip() if extracted else ""
            if not extracted:
                result["content_error"] = "No main content extracted"
        except Exception as e:
            result["content"] = ""
            result["content_error"] = f"Extraction failed: {e}"

        return result

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
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