"""Tests for ScreenshotTool."""

from pathlib import Path

import pytest
from PIL import Image

from jarvis.tools.basic.screenshot import ScreenshotTool


def test_screenshot_schema():
    tool = ScreenshotTool()
    assert tool.name == "screenshot"
    assert tool.category == "basic"
    assert len(tool.schema.parameters) == 2


@pytest.mark.asyncio
async def test_screenshot_execute_full(tmp_path: Path, monkeypatch):
    save_file = tmp_path / "test_screen.png"
    tool = ScreenshotTool()

    def fake_take_screenshot(target_path: Path, region_str: str = "full"):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (100, 100), color="red")
        img.save(str(target_path))
        return 100, 100

    monkeypatch.setattr("jarvis.tools.basic.screenshot._take_screenshot", fake_take_screenshot)

    result = await tool.execute(save_path=str(save_file))
    assert "Screenshot saved successfully" in result
    assert save_file.exists()
    assert save_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_screenshot_execute_region(tmp_path: Path, monkeypatch):
    save_file = tmp_path / "test_region.png"
    tool = ScreenshotTool()

    def fake_take_screenshot(target_path: Path, region_str: str = "full"):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(str(target_path))
        return 50, 50

    monkeypatch.setattr("jarvis.tools.basic.screenshot._take_screenshot", fake_take_screenshot)

    result = await tool.execute(region="0,0,50,50", save_path=str(save_file))
    assert "Screenshot saved successfully" in result
    assert save_file.exists()
    assert save_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_screenshot_invalid_region():
    tool = ScreenshotTool()
    result = await tool.execute(region="invalid_region")
    assert "Error taking screenshot" in result
