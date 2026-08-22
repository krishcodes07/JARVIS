"""
Browser Control Tool — Open URLs, search queries, and manage browser tabs.
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Any

from jarvis.automation.controller import DesktopController
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class BrowserControlTool(BaseTool):
    """Open websites, URLs, search queries, and control browser tabs."""

    schema = ToolSchema(
        name="browser_control",
        description="Open websites or search queries in the web browser, open/close tabs, or open incognito windows.",
        category="desktop",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'open_url', 'search', 'new_tab', 'close_tab', 'switch_tab', 'reopen_tab', 'incognito'.",
                enum=["open_url", "search", "new_tab", "close_tab", "switch_tab", "reopen_tab", "incognito"],
                required=True,
            ),
            ToolParameter(
                name="url",
                type="string",
                description="URL or website to open (e.g. 'https://youtube.com', 'github.com/krishcodes07').",
                required=False,
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search query string (for 'search' action).",
                required=False,
            ),
            ToolParameter(
                name="browser",
                type="string",
                description="Specific browser to use: 'default', 'chrome', 'edge', 'brave', 'firefox'.",
                required=False,
                default="default",
            ),
        ],
        keywords=["browser", "website", "url", "open site", "youtube", "google", "search web", "tab"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.controller = DesktopController()

    async def execute(self, **kwargs: Any) -> str:
        """Execute browser control action."""
        action = kwargs.get("action", "").lower().strip()
        url = kwargs.get("url", "").strip()
        query = kwargs.get("query", "").strip()
        browser_name = kwargs.get("browser", "default").lower().strip()

        if action == "open_url":
            if not url:
                return "Error: 'url' parameter is required for 'open_url' action."
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            ok = await asyncio.to_thread(self.controller.open_url, url, browser_name)
            if ok:
                browser_desc = f" in {browser_name}" if browser_name != "default" else ""
                return f"Opened URL{browser_desc}: {url}"
            return f"Failed to open URL: {url}"

        elif action == "search":
            if not query and url:
                query = url
            if not query:
                return "Error: 'query' parameter is required for 'search' action."
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            ok = await asyncio.to_thread(self.controller.open_url, search_url, browser_name)
            if ok:
                browser_desc = f" in {browser_name}" if browser_name != "default" else ""
                return f"Searched for '{query}'{browser_desc}: {search_url}"
            return f"Failed to search for '{query}'."

        elif action == "new_tab":
            await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "t")
            if url:
                await asyncio.sleep(0.2)
                await asyncio.to_thread(self.controller.type_text, url)
                await asyncio.to_thread(self.controller.press_key, "enter")
                return f"Opened new tab with URL: {url}"
            return "Opened a new browser tab (Ctrl+T)."

        elif action == "close_tab":
            await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "w")
            return "Closed active browser tab (Ctrl+W)."

        elif action == "reopen_tab":
            await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "shift", "t")
            return "Reopened last closed tab (Ctrl+Shift+T)."

        elif action == "switch_tab":
            await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "tab")
            return "Switched to next browser tab (Ctrl+Tab)."

        elif action == "incognito":
            if browser_name in ("chrome", "brave", "edge"):
                await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "shift", "n")
            else:
                await asyncio.to_thread(self.controller.press_hotkey, "ctrl", "shift", "p")
            return "Opened new Incognito / Private window."

        else:
            return f"Unknown action '{action}'. Valid actions: open_url, search, new_tab, close_tab, switch_tab, reopen_tab, incognito."
