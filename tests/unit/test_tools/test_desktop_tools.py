"""
Unit tests for Discrete Desktop Tools.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.desktop.app_control import AppControlTool
from jarvis.tools.desktop.automate_task import AutomateTaskTool
from jarvis.tools.desktop.browser_control import BrowserControlTool
from jarvis.tools.desktop.input_simulation import InputSimulationTool
from jarvis.tools.desktop.media_control import MediaControlTool
from jarvis.tools.desktop.system_settings import SystemSettingsTool
from jarvis.tools.desktop.window_control import WindowControlTool


@pytest.mark.asyncio
async def test_app_control_tool() -> None:
    tool = AppControlTool()
    with patch.object(tool.controller, "launch_app", return_value="Launched notepad.exe"):
        res = await tool.execute(action="launch", app_name="notepad")
        assert "Launched notepad.exe" in res

    with patch.object(tool.controller, "focus_window", return_value=True):
        res_focus = await tool.execute(action="focus", app_name="Notepad")
        assert "Successfully focused" in res_focus


@pytest.mark.asyncio
async def test_browser_control_tool() -> None:
    tool = BrowserControlTool()
    with patch.object(tool.controller, "open_url", return_value=True) as mock_open:
        res = await tool.execute(action="open_url", url="https://youtube.com")
        mock_open.assert_called_once_with("https://youtube.com", "default")
        assert "Opened URL" in res


@pytest.mark.asyncio
async def test_window_control_tool() -> None:
    tool = WindowControlTool()
    with patch.object(tool.controller, "maximize_window", return_value=True):
        res = await tool.execute(action="maximize", window_title="Notepad")
        assert "Maximized" in res

    with patch.object(tool.controller, "snap_window", return_value=True):
        res_snap = await tool.execute(action="snap", window_title="Notepad", direction="left")
        assert "Snapped" in res_snap


@pytest.mark.asyncio
async def test_media_control_tool() -> None:
    tool = MediaControlTool()
    with patch.object(tool.controller, "set_master_volume", return_value=40):
        res = await tool.execute(action="set_volume", volume=40)
        assert "System volume set to 40%" in res

    with patch.object(tool.controller, "send_media_key") as mock_media:
        res_play = await tool.execute(action="play_pause")
        mock_media.assert_called_once_with("play_pause")
        assert "Play/Pause" in res_play


@pytest.mark.asyncio
async def test_system_settings_tool() -> None:
    tool = SystemSettingsTool()
    with patch.object(tool.controller, "lock_workstation", return_value=True):
        res = await tool.execute(action="lock")
        assert "Workstation locked successfully" in res

    with patch.object(tool.controller, "send_toast_notification") as mock_toast:
        res_toast = await tool.execute(action="notify", title="Test", message="Hello")
        mock_toast.assert_called_once_with("Test", "Hello")
        assert "Toast notification sent" in res_toast


@pytest.mark.asyncio
async def test_input_simulation_tool() -> None:
    tool = InputSimulationTool()
    with patch.object(tool.controller, "click", return_value=(200, 300)):
        res = await tool.execute(action="click", x=200, y=300)
        assert "Clicked mouse at (200, 300)" in res

    with patch.object(tool.controller, "type_text") as mock_type:
        res_type = await tool.execute(action="type", text="test typing")
        mock_type.assert_called_once_with("test typing")
        assert "Typed text" in res_type
