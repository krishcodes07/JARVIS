import pytest

from jarvis.core.config import JarvisConfig
from jarvis.tools.basic.list_tools import ListToolsTool


@pytest.mark.asyncio
async def test_list_tools_execute():
    config = JarvisConfig()
    tool = ListToolsTool()
    tool.configure(config)

    res = await tool.execute()
    assert "list_tools" in res
    assert "get_schema" in res
    assert ", " in res
    assert "Available Tools" not in res  # Ensures descriptions/headers are removed
