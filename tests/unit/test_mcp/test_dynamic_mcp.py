"""
Unit tests for Dynamic MCP Server lifecycle and discovery.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.core.config import JarvisConfig
from jarvis.core.engine import JarvisEngine, get_active_engine
from jarvis.mcp.manager import MCPManager
from jarvis.mcp.platform.models import RegisteredTool
from jarvis.mcp.platform.registry import platform_registry
from jarvis.tools.basic.get_schema import GetSchemaTool
from jarvis.tools.basic.list_tools import ListToolsTool
from jarvis.tools.basic.mcp_creator import MCPCreatorTool


@pytest.mark.asyncio
async def test_dynamic_mcp_registration_and_discovery():
    """Verify that custom MCP servers can be registered and enumerated."""
    config = JarvisConfig()
    mgr = MCPManager(config)

    mgr.registry.register("github-dynamic", {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "transport": "stdio",
        "description": "GitHub MCP integration",
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token"},
        "enabled": True,
    })

    servers = mgr.get_available_servers()
    matching = [s for s in servers if s["name"] == "github-dynamic"]
    assert len(matching) == 1
    assert matching[0]["description"] == "GitHub MCP integration"
    assert matching[0]["configured"] is True


@pytest.mark.asyncio
async def test_dynamic_mcp_platform_tools():
    """Verify that dynamic tools registered into platform_registry are tracked."""
    tool = RegisteredTool(
        name="query_db",
        qualified_name="postgres__query_db",
        server_name="postgres",
        description="Execute SQL query",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )

    platform_registry.register_tool(tool)
    assert platform_registry.has_tool("postgres__query_db") is True

    tools = platform_registry.find_tools(server="postgres")
    assert len(tools) == 1
    assert tools[0].name == "query_db"

    platform_registry.unregister_server("postgres")
    assert platform_registry.has_tool("postgres__query_db") is False


@pytest.mark.asyncio
async def test_realtime_mcp_creator_tool_execution(monkeypatch):
    """Verify that MCPCreatorTool auto-resolves active engine and connects live in real time."""
    engine = JarvisEngine()
    engine.config = JarvisConfig()
    engine.mcp_manager = MagicMock()
    engine.mcp_manager.registry = MagicMock()

    # Mock connection result
    mock_conn = MagicMock()
    mock_tool = MagicMock()
    mock_tool.name = "scrape"
    mock_conn.tools = [mock_tool]
    engine.mcp_manager.client = MagicMock()
    engine.mcp_manager.client.connections = {"firecrawl": mock_conn}
    engine.mcp_manager.connect_server = AsyncMock(return_value=(True, "Connected"))

    # Register engine as active
    monkeypatch.setattr("jarvis.core.engine._ACTIVE_ENGINE", engine)
    assert get_active_engine() is engine

    creator = MCPCreatorTool()
    creator.configure(engine.config)
    res = await creator.execute(
        name="firecrawl",
        command="npx",
        args=["-y", "firecrawl-mcp"],
        env={"FIRECRAWL_API_KEY": "fc-test"},
        auto_connect=True,
    )

    assert "✅" in res
    assert "firecrawl" in res
    assert "Connected" in res
    engine.mcp_manager.connect_server.assert_awaited_once_with("firecrawl")

    # Also verify get_schema and list_tools with registered tools
    sample_tool = RegisteredTool(
        name="scrape",
        qualified_name="firecrawl__scrape",
        server_name="firecrawl",
        description="Scrape URL",
        input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
    )
    platform_registry.register_tool(sample_tool)

    schema_tool = GetSchemaTool()
    schema_tool.configure(engine.config)
    # Check short name lookup
    schema_res = await schema_tool.execute(tool_names=["scrape"])
    assert "firecrawl__scrape" in schema_res or "scrape" in schema_res

    # Check list_tools
    list_tool = ListToolsTool()
    list_tool.configure(engine.config)
    list_res = await list_tool.execute()
    assert "firecrawl__scrape" in list_res

    platform_registry.unregister_server("firecrawl")
