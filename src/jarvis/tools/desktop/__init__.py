"""
Desktop Automation Tools — Native OS, browser, window, media, system and input simulation tools.
"""

from jarvis.tools.desktop.app_control import AppControlTool
from jarvis.tools.desktop.automate_task import AutomateTaskTool
from jarvis.tools.desktop.browser_control import BrowserControlTool
from jarvis.tools.desktop.input_simulation import InputSimulationTool
from jarvis.tools.desktop.media_control import MediaControlTool
from jarvis.tools.desktop.system_settings import SystemSettingsTool
from jarvis.tools.desktop.window_control import WindowControlTool

__all__ = [
    "AppControlTool",
    "AutomateTaskTool",
    "BrowserControlTool",
    "InputSimulationTool",
    "MediaControlTool",
    "SystemSettingsTool",
    "WindowControlTool",
]
