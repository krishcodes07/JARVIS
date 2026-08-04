"""Tests for GetToolsTool and BaseTool category property."""

import pytest
from jarvis.tools.basic.get_tools import GetToolsTool
from jarvis.tools.base import BaseTool, ToolSchema


class DummyTool(BaseTool):
    schema = ToolSchema(
        name="dummy_tool",
        description="A dummy tool for testing.",
        category="testing",
    )

    async def execute(self, **kwargs) -> str:
        return "ok"


def test_base_tool_category_property():
    tool = DummyTool()
    assert tool.name == "dummy_tool"
    assert tool.description == "A dummy tool for testing."
    assert tool.category == "testing"


@pytest.mark.asyncio
async def test_get_tools_execute():
    tool = GetToolsTool()
    result = await tool.execute()
    assert "Available Tools" in result
