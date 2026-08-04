"""Tests for ScreenshotTool."""

from pathlib import Path
import pytest
from jarvis.tools.basic.screenshot import ScreenshotTool, _take_screenshot


def test_screenshot_schema():
    tool = ScreenshotTool()
    assert tool.name == "screenshot"
    assert tool.category == "basic"
    assert len(tool.schema.parameters) == 2


@pytest.mark.asyncio
async def test_screenshot_execute_full(tmp_path: Path):
    save_file = tmp_path / "test_screen.png"
    tool = ScreenshotTool()
    result = await tool.execute(save_path=str(save_file))
    assert "Screenshot saved successfully" in result
    assert save_file.exists()
    assert save_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_screenshot_execute_region(tmp_path: Path):
    save_file = tmp_path / "test_region.png"
    tool = ScreenshotTool()
    result = await tool.execute(region="0,0,100,100", save_path=str(save_file))
    assert "Screenshot saved successfully" in result
    assert save_file.exists()
    assert save_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_screenshot_invalid_region():
    tool = ScreenshotTool()
    result = await tool.execute(region="invalid_region")
    assert "Error taking screenshot" in result
