"""
Unit tests for basic/web tools: web_search and read_url.
"""

import pytest

from jarvis.core.config import JarvisConfig
from jarvis.tools.basic.read_url import ReadUrlTool
from jarvis.tools.basic.web_search import WebSearchTool
from jarvis.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_web_tools_discovery():
    config = JarvisConfig.load()
    registry = ToolRegistry(config)
    registry.discover_tools()

    assert "web_search" in registry
    assert "read_url" in registry

    ws_tool = registry.get("web_search")
    assert ws_tool.category == "basic"
    assert ws_tool.schema.name == "web_search"

    ru_tool = registry.get("read_url")
    assert ru_tool.category == "basic"
    assert ru_tool.schema.name == "read_url"


@pytest.mark.asyncio
async def test_read_url_html_parsing():
    tool = ReadUrlTool()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page Title</title></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <h1>Welcome to JARVIS</h1>
        <p>This is a <strong>bold</strong> paragraph with <code>code snippet</code>.</p>
        <script>console.log("noisy script");</script>
        <ul>
            <li>Feature 1</li>
            <li>Feature 2</li>
        </ul>
    </body>
    </html>
    """

    markdown_text, page_title = tool._html_to_markdown(sample_html)
    assert page_title == "Test Page Title"
    assert "# Welcome to JARVIS" in markdown_text
    assert "**bold**" in markdown_text
    assert "`code snippet`" in markdown_text
    assert "* Feature 1" in markdown_text
    assert "noisy script" not in markdown_text


@pytest.mark.asyncio
async def test_web_search_html_cleaning():
    tool = WebSearchTool()
    cleaned = tool._clean_html("<b>Python</b> &amp; <i>AsyncIO</i> &lt;3")
    assert cleaned == "Python & AsyncIO <3"
