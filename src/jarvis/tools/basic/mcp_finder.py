"""
MCP Finder Tool — Search for MCP servers on mcpmarket.com and web registries.
"""

from __future__ import annotations

import contextlib
import logging
import urllib.parse
from typing import Any

import httpx

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class MCPFinderTool(BaseTool):
    """Tool for discovering MCP servers on mcpmarket.com and online registries."""

    schema = ToolSchema(
        name="find_mcp",
        description=(
            "Search for Model Context Protocol (MCP) servers on mcpmarket.com and registries. "
            "Returns matching MCP packages, installation commands (npx/uvx), required env vars, "
            "and descriptions. Use this before installing a new MCP integration."
        ),
        category="basic",
        aliases=["search_mcp", "mcp_market", "find_mcp_server", "explore_mcp"],
        keywords=["mcp", "find", "search", "market", "mcpmarket", "integration", "tools"],
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "Search query or service name (e.g. 'postgres', 'github', "
                    "'slack', 'weather', 'notion', 'jira')."
                ),
                required=True,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results to return (default: 5).",
                required=False,
                default=5,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Search mcpmarket and web for MCP servers matching the query."""
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return "❌ Error: Search query is required."

        limit = int(kwargs.get("limit", 5))

        logger.info("Searching MCP Market for '%s'...", query)

        # 1. First attempt: Search mcpmarket / web via DuckDuckGo HTML search
        results = await self._search_mcp_market(query, limit)
        if not results:
            return (
                f"🔍 No specific MCP servers found on MCP Market for '{query}'.\n\n"
                f"**Suggestions:**\n"
                f"- Try broader keywords (e.g. 'database' instead of 'custom-db').\n"
                f"- Check standard packages like `@modelcontextprotocol/server-{query.lower()}`.\n"
                f"- Check https://mcpmarket.com/ or https://github.com/modelcontextprotocol/servers"
            )

        output = [
            f"🔍 **MCP Market Results for '{query}'** (from https://mcpmarket.com/ & ecosystem):\n"
        ]

        for i, item in enumerate(results[:limit], 1):
            title = item.get("title", "MCP Server")
            snippet = item.get("snippet", "")
            url = item.get("url", "https://mcpmarket.com")
            pkg_cmd = item.get("command", "")
            env_vars = item.get("env_vars", [])

            output.append(f"### {i}. {title}")
            if snippet:
                output.append(f"**Description**: {snippet}")
            if pkg_cmd:
                output.append(f"- **Install Command**: `{pkg_cmd}`")
            if env_vars:
                output.append(f"- **Required Env / Keys**: `{', '.join(env_vars)}`")
            output.append(f"- **Market Link**: {url}\n")

        output.append(
            "\n💡 **To install**, call `mcp_creator` with the command and keys, "
            "or press `Ctrl+A` in the TUI MCP modal."
        )
        return "\n".join(output)

    async def _search_mcp_market(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Query web search focused on mcpmarket and official modelcontextprotocol servers."""
        search_query = f"site:mcpmarket.com {query} OR modelcontextprotocol server {query}"
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        results: list[dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    results = self._parse_search_html(res.text)
        except Exception as e:
            logger.debug("Web search failed for MCP Market: %s", e)

        # Fallback to curated heuristics if web scrape is blocked or empty
        if not results:
            results = self._get_fallback_suggestions(query)

        return results

    def _parse_search_html(self, html_text: str) -> list[dict[str, Any]]:
        """Extract search results from DuckDuckGo HTML response."""
        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results: list[dict[str, str]] = []
                self.in_result = False
                self.in_title = False
                self.in_snippet = False
                self.curr_url = ""
                self.curr_title = ""
                self.curr_snippet = ""

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                classes = attrs_dict.get("class", "")
                if tag == "a" and "result__snippet" in classes:
                    self.in_snippet = True
                elif tag == "a" and "result__url" in classes:
                    pass
                elif tag == "a" and "result__a" in classes:
                    self.in_title = True
                    href = attrs_dict.get("href", "")
                    # Extract target URL from DuckDuckGo redirect wrapper if present
                    if "uddg=" in href:
                        try:
                            parsed_url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            self.curr_url = parsed_url.get("uddg", [href])[0]
                        except Exception:
                            self.curr_url = href
                    else:
                        self.curr_url = href

            def handle_endtag(self, tag):
                if tag == "a" and self.in_title:
                    self.in_title = False
                elif tag == "a" and self.in_snippet:
                    self.in_snippet = False
                    if self.curr_title and self.curr_url:
                        self.results.append({
                            "title": self.curr_title.strip(),
                            "url": self.curr_url.strip(),
                            "snippet": self.curr_snippet.strip(),
                        })
                        self.curr_title = ""
                        self.curr_url = ""
                        self.curr_snippet = ""

            def handle_data(self, data):
                if self.in_title:
                    self.curr_title += data
                elif self.in_snippet:
                    self.curr_snippet += data

        parser = DDGParser()
        with contextlib.suppress(Exception):
            parser.feed(html_text)

        parsed_items: list[dict[str, Any]] = []
        for r in parser.results:
            title = r["title"]
            snippet = r["snippet"]
            url = r["url"]

            # Infer command
            cmd = ""
            if "npx" in snippet or "npx" in title:
                for word in (snippet + " " + title).split():
                    clean_w = word.strip("`(),.'\"")
                    if clean_w.startswith("@") or "server-" in clean_w or "-mcp" in clean_w:
                        cmd = f"npx -y {clean_w}"
                        break
            elif "uvx" in snippet or "uvx" in title:
                for word in (snippet + " " + title).split():
                    clean_w = word.strip("`(),.'\"")
                    if "mcp" in clean_w or "server" in clean_w:
                        cmd = f"uvx {clean_w}"
                        break

            if not cmd:
                # Clean title slug for fallback
                first_word = title.split()[0].lower().replace("-mcp", "").replace(":", "")
                cmd = f"npx -y @modelcontextprotocol/server-{first_word}"

            parsed_items.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "command": cmd,
                "env_vars": self._extract_env_vars(snippet),
            })
        return parsed_items

    def _extract_env_vars(self, text: str) -> list[str]:
        """Detect common environment variable patterns like API_KEY, TOKEN, etc."""
        import re
        matches = re.findall(r"\b[A-Z0-9_]{3,30}_(?:KEY|TOKEN|SECRET|URL|URI|PASSWORD|ID)\b", text)
        return list(dict.fromkeys(matches))

    def _get_fallback_suggestions(self, query: str) -> list[dict[str, Any]]:
        """Return high-signal fallback MCP packages for standard searches."""
        clean = query.lower().strip()
        common_catalog = {
            "postgres": {
                "title": "PostgreSQL MCP Server",
                "snippet": "SQL querying, schema inspection, and table analysis for Postgres.",
                "command": "npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb",
                "env_vars": ["POSTGRES_URL"],
                "url": "https://mcpmarket.com/server/postgres",
            },
            "postgresql": {
                "title": "PostgreSQL MCP Server",
                "snippet": "SQL querying, schema inspection, and table analysis for Postgres.",
                "command": "npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb",
                "env_vars": ["POSTGRES_URL"],
                "url": "https://mcpmarket.com/server/postgres",
            },
            "github": {
                "title": "GitHub MCP Server",
                "snippet": "Search repositories, read code, view issues, and manage pull requests.",
                "command": "npx -y @modelcontextprotocol/server-github",
                "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
                "url": "https://mcpmarket.com/server/github",
            },
            "slack": {
                "title": "Slack MCP Server",
                "snippet": "List channels, post messages, and read thread histories in Slack.",
                "command": "npx -y @modelcontextprotocol/server-slack",
                "env_vars": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
                "url": "https://mcpmarket.com/server/slack",
            },
            "sqlite": {
                "title": "SQLite MCP Server",
                "snippet": "Direct SQL querying and schema inspection on SQLite database files.",
                "command": "npx -y @modelcontextprotocol/server-sqlite /path/to/database.db",
                "env_vars": [],
                "url": "https://mcpmarket.com/server/sqlite",
            },
            "filesystem": {
                "title": "Filesystem MCP Server",
                "snippet": "Secure local directory access for listing, reading, and writing files.",
                "command": "npx -y @modelcontextprotocol/server-filesystem C:\\allowed_dir",
                "env_vars": [],
                "url": "https://mcpmarket.com/server/filesystem",
            },
            "brave": {
                "title": "Brave Search MCP Server",
                "snippet": "Fast, private web and local search using the Brave Search API.",
                "command": "npx -y @modelcontextprotocol/server-brave-search",
                "env_vars": ["BRAVE_API_KEY"],
                "url": "https://mcpmarket.com/server/brave-search",
            },
            "puppeteer": {
                "title": "Puppeteer MCP Server",
                "snippet": "Browser automation for webpage navigation, screenshots, and scraping.",
                "command": "npx -y @modelcontextprotocol/server-puppeteer",
                "env_vars": [],
                "url": "https://mcpmarket.com/server/puppeteer",
            },
            "notion": {
                "title": "Notion MCP Server",
                "snippet": "Search workspace pages, read databases, and append blocks to Notion.",
                "command": "npx -y @modelcontextprotocol/server-notion",
                "env_vars": ["NOTION_API_KEY"],
                "url": "https://mcpmarket.com/server/notion",
            },
        }

        if clean in common_catalog:
            return [common_catalog[clean]]

        for k, v in common_catalog.items():
            if clean in k or k in clean:
                return [v]

        return [
            {
                "title": f"{query.capitalize()} MCP Server",
                "snippet": f"Model Context Protocol integration for {query}.",
                "command": f"npx -y @modelcontextprotocol/server-{clean}",
                "env_vars": [f"{clean.upper()}_API_KEY"],
                "url": f"https://mcpmarket.com/server/{clean}",
            }
        ]
