"""
Unit tests for Advanced Tool RAG, Query Expansion, Lexical Matching, and SearchTools Meta-Tool.
"""

import pytest

from jarvis.providers.base import ToolDefinition
from jarvis.tools.basic.search_tools import SearchToolsTool
from jarvis.tools.rag import ToolRetriever


@pytest.mark.asyncio
async def test_acronym_and_alias_retrieval():
    retriever = ToolRetriever()

    tools = [
        ToolDefinition(
            name="telegram_get_messages",
            description="Fetch recent messages from Telegram chat or bot.",
            category="messaging",
            aliases=["tg", "telegram", "tg chat"],
            keywords=["messages", "chat", "direct message"],
        ),
        ToolDefinition(
            name="calculator",
            description="Perform mathematical calculations.",
            category="basic",
            aliases=["math", "calc"],
            keywords=["calculate", "math"],
        ),
        ToolDefinition(
            name="terminal_run",
            description="Run command in terminal.",
            category="system",
            aliases=["shell", "cmd"],
        ),
    ]

    # Test retrieval with acronym "tg"
    retrieved = await retriever.retrieve(query="check recent messages from tg", all_tools=tools, top_k=2)
    names = [t.name for t in retrieved]
    assert "telegram_get_messages" in names


@pytest.mark.asyncio
async def test_implicit_intent_query_expansion():
    retriever = ToolRetriever()

    tools = [
        ToolDefinition(
            name="firecrawl_scrape",
            description="Scrape and extract text content from any webpage using Firecrawl.",
            category="web",
            aliases=["scrape", "web scrape", "firecrawl"],
            keywords=["scrape", "fetch url", "web page"],
        ),
        ToolDefinition(
            name="calculator",
            description="Perform mathematical calculations.",
            category="basic",
        ),
        ToolDefinition(
            name="file_writer",
            description="Write content to a file.",
            category="filesystem",
        ),
    ]

    # Query with implicit research intent
    retrieved = await retriever.retrieve(
        query="new cookie Isaac 28b model tell me about it",
        all_tools=tools,
        top_k=2
    )
    names = [t.name for t in retrieved]
    assert "firecrawl_scrape" in names


@pytest.mark.asyncio
async def test_search_tools_meta_tool():
    search_tool = SearchToolsTool()

    res = await search_tool.execute(query="tg")
    assert isinstance(res, str)
    assert len(res) > 0


@pytest.mark.asyncio
async def test_engine_tool_rag_initialization():
    from jarvis.core.engine import JarvisEngine
    engine = JarvisEngine()
    tools = await engine._get_all_raw_tool_definitions()
    assert isinstance(tools, list)
    summary = engine._get_capability_summary(tools)
    assert isinstance(summary, str)

