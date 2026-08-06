"""Unit tests for Tool RAG functionality."""

import pytest

from jarvis.providers.base import ToolDefinition
from jarvis.tools.rag import ToolRetriever


@pytest.mark.asyncio
async def test_tool_retriever_fallback():
    retriever = ToolRetriever()
    await retriever.initialize()

    tools = [
        ToolDefinition(name="run_command", description="Run bash command", parameters={}),
        ToolDefinition(name="calculator", description="Math calculator", parameters={}),
        ToolDefinition(name="gmail_send", description="Send emails", parameters={}),
    ]

    # Without embedder, it should safely return fallback tools
    selected = await retriever.retrieve(
        query="Send email",
        all_tools=tools,
        top_k=2,
        always_include=["run_command"],
    )

    assert len(selected) == 2
    assert selected[0].name == "run_command"


@pytest.mark.asyncio
async def test_tool_retriever_all_tools_smaller_than_top_k():
    retriever = ToolRetriever()
    tools = [
        ToolDefinition(name="run_command", description="Run command", parameters={}),
    ]
    selected = await retriever.retrieve("any query", tools, top_k=5)
    assert len(selected) == 1
    assert selected[0].name == "run_command"
