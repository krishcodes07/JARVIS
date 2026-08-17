"""
UIA Grounder — Windows UI Automation Accessibility Tree Inspector.

Parses the native Windows UI Automation control hierarchy for active windows,
extracting interactive controls with bounding boxes and center coordinates.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from jarvis.automation.grounding.screen import ScreenManager
from jarvis.automation.schemas import UIElementInfo, WindowInfo

logger = logging.getLogger(__name__)

# Interactive control types worth extracting for automation
INTERACTIVE_CONTROL_TYPES = {
    "Button",
    "Edit",
    "CheckBox",
    "RadioButton",
    "ComboBox",
    "ListItem",
    "MenuItem",
    "Hyperlink",
    "TabItem",
    "TreeItem",
    "ToolBar",
    "SplitButton",
    "Custom",
    "Document",
}


class UIAGrounder:
    """Extracts and indexes UI elements using Windows UI Automation (UIA)."""

    def __init__(self) -> None:
        self.screen_manager = ScreenManager()
        self._cached_elements: dict[int, Any] = {}

    def get_active_window_info(self) -> WindowInfo | None:
        """Retrieve metadata of the currently focused window."""
        if sys.platform != "win32":
            return None

        try:
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title_str = win32gui.GetWindowText(hwnd) or ""
            class_str = win32gui.GetClassName(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
            width = max(0, rect[2] - rect[0])
            height = max(0, rect[3] - rect[1])

            return WindowInfo(
                handle=hwnd,
                title=title_str,
                class_name=class_str,
                process_id=pid,
                is_active=True,
                rect=rect,
                width=width,
                height=height,
            )
        except Exception as e:
            logger.debug(f"Error getting active window info: {e}")
            return None

    def list_open_windows(self) -> list[WindowInfo]:
        """List all visible top-level application windows."""
        if sys.platform != "win32":
            return []

        windows: list[WindowInfo] = []
        try:
            import win32gui
            import win32process

            fg_hwnd = win32gui.GetForegroundWindow()

            def enum_cb(hwnd: int, _: Any) -> bool:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                raw_title = win32gui.GetWindowText(hwnd)
                if not raw_title or not raw_title.strip():
                    return True

                # Filter out tooltips, shell flyouts with zero size
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w <= 10 or h <= 10:
                    return True

                raw_class = win32gui.GetClassName(hwnd)
                class_name_str = raw_class or ""
                # Filter out Progman / WorkerW background shell
                if class_name_str in ("Progman", "WorkerW", "Shell_TrayWnd"):
                    return True

                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                windows.append(
                    WindowInfo(
                        handle=hwnd,
                        title=raw_title.strip(),
                        class_name=class_name_str,
                        process_id=pid,
                        is_active=(hwnd == fg_hwnd),
                        rect=rect,
                        width=w,
                        height=h,
                    )
                )
                return True

            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.warning(f"Error enumerating open windows: {e}")

        return windows

    def extract_interactive_elements(
        self,
        window_handle: int | None = None,
        max_elements: int = 60,
    ) -> list[UIElementInfo]:
        """Inspect the active window or specific window handle and extract interactive controls.

        Returns a list of structured UIElementInfo objects with unique 1-based IDs.
        """
        if sys.platform != "win32":
            return []

        self._cached_elements.clear()
        results: list[UIElementInfo] = []

        try:
            from pywinauto import Desktop

            desktop = Desktop(backend="uia")
            active_win = None

            if window_handle:
                try:
                    active_win = desktop.window(handle=window_handle)
                except Exception:
                    pass

            if active_win is None:
                # Target foreground window
                try:
                    import win32gui
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        active_win = desktop.window(handle=hwnd)
                except Exception:
                    pass

            if active_win is None:
                return []

            # Retrieve descendants
            descendants = active_win.descendants()
            element_id = 1
            screen_bounds = self.screen_manager.get_screen_bounds()

            for elem in descendants:
                try:
                    ctrl_type = elem.element_info.control_type or ""
                    name = elem.element_info.name or ""
                    auto_id = elem.element_info.automation_id or ""
                    class_name = elem.element_info.class_name or ""

                    # Only process interactive controls or controls with explicit names
                    if ctrl_type not in INTERACTIVE_CONTROL_TYPES and not name.strip():
                        continue

                    # Check element visibility and rect
                    rect = elem.rectangle()
                    width = rect.width()
                    height = rect.height()

                    # Filter out degenerate or invisible rects
                    if width <= 4 or height <= 4:
                        continue

                    # Filter out off-screen elements
                    if (
                        rect.right <= screen_bounds.left
                        or rect.left >= screen_bounds.right
                        or rect.bottom <= screen_bounds.top
                        or rect.top >= screen_bounds.bottom
                    ):
                        continue

                    center_x = rect.left + (width // 2)
                    center_y = rect.top + (height // 2)

                    # Clamp to primary screen bounds
                    cx, cy = self.screen_manager.clamp_coordinates(center_x, center_y)

                    ui_info = UIElementInfo(
                        id=element_id,
                        name=name.strip() if name else f"<{ctrl_type}>",
                        control_type=ctrl_type,
                        automation_id=auto_id,
                        class_name=class_name,
                        bounding_box=(rect.left, rect.top, width, height),
                        center_point=(cx, cy),
                        is_enabled=elem.is_enabled() if hasattr(elem, "is_enabled") else True,
                        is_keyboard_focusable=elem.is_keyboard_focusable() if hasattr(elem, "is_keyboard_focusable") else False,
                    )

                    self._cached_elements[element_id] = elem
                    results.append(ui_info)
                    element_id += 1

                    if len(results) >= max_elements:
                        break
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"UIA element extraction notice: {e}")

        return results

    def get_element_by_id(self, element_id: int) -> Any | None:
        """Get the cached native pywinauto wrapper element by its 1-based ID."""
        return self._cached_elements.get(element_id)

    def format_elements_for_prompt(self, elements: list[UIElementInfo]) -> str:
        """Format the list of detected UI elements into a compact readable table for the LLM."""
        if not elements:
            return "No interactive UI elements detected in the active window."

        lines = ["| ID | Control Type | Name / Text | Coordinates (X, Y) | Automation ID |"]
        lines.append("|---|---|---|---|---|")
        for el in elements:
            cx, cy = el.center_point
            name = el.name.replace("|", "/") if el.name else ""
            auto_id = el.automation_id.replace("|", "/") if el.automation_id else ""
            lines.append(f"| {el.id} | {el.control_type} | {name} | ({cx}, {cy}) | {auto_id} |")

        return "\n".join(lines)
