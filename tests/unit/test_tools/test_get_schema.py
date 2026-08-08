import pytest
from jarvis.core.config import JarvisConfig
from jarvis.tools.basic.get_schema import GetSchemaTool


@pytest.mark.asyncio
async def test_get_schema_execute():
    config = JarvisConfig()
    tool = GetSchemaTool()
    tool.configure(config)

    res = await tool.execute(tool_names=["read_file", "list_tools"])
    assert "Schema for 'read_file'" in res
    assert "Schema for 'list_tools'" in res


@pytest.mark.asyncio
async def test_get_schema_missing_tool():
    config = JarvisConfig()
    tool = GetSchemaTool()
    tool.configure(config)

    res = await tool.execute(tool_names=["non_existent_tool_name_xyz"])
    assert "No tools found" in res or "Could not find" in res
