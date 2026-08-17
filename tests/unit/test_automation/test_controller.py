"""
Unit tests for DesktopController and ScreenManager.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from jarvis.automation.controller import DesktopController
from jarvis.automation.grounding.screen import ScreenManager


def test_screen_manager_clamping() -> None:
    sm = ScreenManager()
    with patch.object(sm, "get_primary_resolution", return_value=(1920, 1080)):
        cx, cy = sm.clamp_coordinates(-10, -50)
        assert cx == 0
        assert cy == 0

        cx2, cy2 = sm.clamp_coordinates(2000, 1500)
        assert cx2 == 1919
        assert cy2 == 1079


def test_screen_manager_normalization() -> None:
    sm = ScreenManager()
    with patch.object(sm, "get_primary_resolution", return_value=(1920, 1080)):
        px, py = sm.normalized_to_pixels(0.5, 0.5)
        assert px == 960
        assert py == 540

        nx, ny = sm.pixels_to_normalized(960, 540)
        assert nx == 0.5
        assert ny == 0.5


def test_resolve_executable_dynamic() -> None:
    controller = DesktopController()
    with patch("shutil.which", return_value="C:\\Windows\\system32\\notepad.exe"):
        resolved = controller.resolve_executable("notepad")
        assert resolved == "C:\\Windows\\system32\\notepad.exe"


def test_controller_mouse_actions_mocked() -> None:
    controller = DesktopController()
    with patch("pyautogui.moveTo") as mock_move, patch("pyautogui.click") as mock_click:
        with patch.object(controller.screen, "get_primary_resolution", return_value=(1920, 1080)):
            controller.move_to(500, 300, duration=0.0)
            mock_move.assert_called_once_with(500, 300)

            controller.click(x=500, y=300)
            mock_click.assert_called_once()


def test_controller_keyboard_typing_mocked() -> None:
    controller = DesktopController()
    with patch("pyautogui.typewrite") as mock_typewrite, patch("pyautogui.hotkey") as mock_hotkey:
        controller.type_text("Hello World", use_clipboard_fallback=False)
        mock_typewrite.assert_called_once_with("Hello World", interval=0.02)

        controller.press_hotkey("ctrl", "c")
        mock_hotkey.assert_called_once_with("ctrl", "c")


def test_close_window_does_not_close_foreground_when_not_found() -> None:
    controller = DesktopController()
    with patch.object(controller, "find_windows", return_value=[]):
        # When target app is not found, close_window should return False and NOT close active window
        closed = controller.close_window("non_existent_app_xyz")
        assert not closed


def test_close_window_closes_matched_handles() -> None:
    controller = DesktopController()
    with patch.object(controller, "find_windows", return_value=[12345]):
        with patch("win32gui.IsWindow", return_value=True), patch("win32gui.PostMessage") as mock_post:
            closed = controller.close_window("notepad")
            assert closed
            mock_post.assert_called_once()
