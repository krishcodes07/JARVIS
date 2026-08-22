"""
Desktop Controller — Native OS, Mouse, Keyboard, Window, App and Media Actuation.

Provides reliable low-level execution primitives for Windows automation:
- Human-like smooth mouse motion and clicks
- Safe keyboard typing with unicode clipboard fallback
- Native window management (focus, maximize, snap, resize)
- App launching and system media/audio control
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

from jarvis.automation.grounding.screen import ScreenManager
from jarvis.automation.safety import SafetyGuard

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from jarvis.core.config import AutomationConfig

logger = logging.getLogger(__name__)

# Virtual Keycodes for Media Keys
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF


class DesktopController:
    """Low-level OS controller for executing physical desktop actions."""

    def __init__(
        self,
        config: AutomationConfig | None = None,
        safety_guard: SafetyGuard | None = None,
    ) -> None:
        self.config = config
        self.safety = safety_guard or SafetyGuard(config)
        self.screen = ScreenManager()

    # ─── Mouse Actions ──────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float | None = None) -> tuple[int, int]:
        """Move cursor to (x, y) with smooth easing."""
        self.safety.assert_not_aborted()
        cx, cy = self.screen.clamp_coordinates(x, y)

        dur = duration if duration is not None else (
            self.config.mouse_speed_seconds if (self.config and self.config.human_mouse_speed) else 0.0
        )

        import pyautogui
        if dur > 0:
            try:
                import pytweening
                tween_fn = pytweening.easeOutQuad
            except Exception:
                tween_fn = getattr(pyautogui, "easeOutQuad", None)

            if tween_fn:
                pyautogui.moveTo(cx, cy, duration=dur, tween=tween_fn)
            else:
                pyautogui.moveTo(cx, cy, duration=dur)
        else:
            pyautogui.moveTo(cx, cy)
        return cx, cy

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> tuple[int, int]:
        """Click at (x, y) or current cursor position."""
        self.safety.assert_not_aborted()
        import pyautogui

        if x is not None and y is not None:
            cx, cy = self.move_to(x, y)
        else:
            pos = pyautogui.position()
            cx, cy = pos.x, pos.y

        pyautogui.click(x=cx, y=cy, button=button, clicks=clicks, interval=interval)
        return cx, cy

    def double_click(self, x: int | None = None, y: int | None = None) -> tuple[int, int]:
        """Double-click at (x, y)."""
        return self.click(x=x, y=y, clicks=2, interval=0.08)

    def right_click(self, x: int | None = None, y: int | None = None) -> tuple[int, int]:
        """Right-click at (x, y)."""
        return self.click(x=x, y=y, button="right")

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.4) -> None:
        """Click and drag from (start_x, start_y) to (end_x, end_y)."""
        self.safety.assert_not_aborted()
        import pyautogui

        self.move_to(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration, button="left")

    def scroll(self, amount: int = 3, direction: str = "down", x: int | None = None, y: int | None = None) -> None:
        """Scroll mouse wheel up or down."""
        self.safety.assert_not_aborted()
        import pyautogui

        if x is not None and y is not None:
            self.move_to(x, y)

        clicks = -abs(amount) if direction.lower() == "down" else abs(amount)
        # Multiply clicks for natural scrolling distance
        pyautogui.scroll(clicks * 120)

    def get_cursor_position(self) -> tuple[int, int]:
        """Get current mouse cursor physical coordinates."""
        import pyautogui
        pos = pyautogui.position()
        return pos.x, pos.y

    # ─── Keyboard Actions ───────────────────────────────────────

    def type_text(
        self,
        text: str,
        interval: float = 0.02,
        use_clipboard_fallback: bool = True,
    ) -> None:
        """Type text string. Uses clipboard paste for multi-line or non-ASCII text for reliability."""
        self.safety.assert_not_aborted()
        import pyautogui

        # If text contains newlines, tabs, or non-ASCII symbols, clipboard paste is much faster & error-free
        needs_clipboard = use_clipboard_fallback and (
            "\n" in text or "\t" in text or any(ord(c) > 127 for c in text) or len(text) > 40
        )

        if needs_clipboard:
            import pyperclip
            prev_clip = pyperclip.paste()
            try:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.05)
            finally:
                # Restore previous clipboard after a brief delay
                try:
                    pyperclip.copy(prev_clip)
                except Exception:
                    pass
        else:
            pyautogui.typewrite(text, interval=interval)

    def press_hotkey(self, *keys: str) -> None:
        """Press a key combination (e.g. 'ctrl', 'c' or 'win', 'r' or 'alt', 'f4')."""
        self.safety.assert_not_aborted()
        import pyautogui

        normalized_keys = [k.strip().lower() for k in keys if k.strip()]
        pyautogui.hotkey(*normalized_keys)

    def press_key(self, key: str, presses: int = 1, interval: float = 0.05) -> None:
        """Press a single key (e.g. 'enter', 'esc', 'tab', 'backspace')."""
        self.safety.assert_not_aborted()
        import pyautogui

        pyautogui.press(key.strip().lower(), presses=presses, interval=interval)

    # ─── Window Management ──────────────────────────────────────

    def find_windows(self, query: str | int | None) -> list[int]:
        """Find matching window handles by title substring, process name, or class name.

        Args:
            query: Window handle (int) or search string (e.g. 'notepad', 'explorer', 'chrome', 'spotify', 'Downloads').

        Returns:
            List of matching HWNDs (empty if none found).
        """
        if sys.platform != "win32" or query is None:
            return []

        # If already an integer HWND
        if isinstance(query, int):
            try:
                import win32gui
                return [query] if win32gui.IsWindow(query) else []
            except Exception:
                return []

        target = query.strip().lower()
        if not target:
            return []

        # Handle 'active' or 'foreground' explicitly
        if target in ("active", "active_window", "foreground", "current"):
            try:
                import win32gui
                fg = win32gui.GetForegroundWindow()
                return [fg] if fg and win32gui.IsWindow(fg) else []
            except Exception:
                return []

        target_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", target).strip()
        target_words = [w for w in target_clean.split() if len(w) > 1]
        if not target_words:
            target_words = [target]

        try:
            import psutil
            import win32gui
            import win32process
        except Exception:
            return []

        scored_matches: list[tuple[int, int]] = []  # (score, hwnd)

        def enum_cb(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True

            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w <= 10 or h <= 10:
                return True

            raw_title = (win32gui.GetWindowText(hwnd) or "").strip()
            raw_class = (win32gui.GetClassName(hwnd) or "").strip()

            # Ignore desktop wallpaper / system tray shells unless explicitly searched
            if raw_class in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                if "shell" not in target and "taskbar" not in target:
                    return True

            # Get process name and process stem
            proc_name = ""
            proc_stem = ""
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name().lower()
                proc_stem = os.path.splitext(proc_name)[0].lower()
            except Exception:
                pass

            title_lower = raw_title.lower()
            class_lower = raw_class.lower()

            # For explorer specifically: only match actual File Explorer folder windows (CabinetWClass/ExploreWClass)
            # or windows with explorer in title, NEVER the background taskbar shell
            if "explorer" in target:
                if proc_name == "explorer.exe" and raw_class not in ("CabinetWClass", "ExploreWClass") and not raw_title:
                    return True

            score = 0

            # 1. Process name matches (highest weight)
            if target == proc_name or target == proc_stem:
                score += 100
            elif target in proc_name or proc_stem in target:
                score += 80

            # 2. Window title matches
            if target == title_lower:
                score += 90
            elif target in title_lower:
                score += 70

            # 3. Token-based word matches
            matched_words = sum(1 for w in target_words if w in title_lower or w in proc_name or w in class_lower)
            if matched_words == len(target_words):
                score += 50 + (10 * matched_words)

            # 4. Class name match
            if target in class_lower:
                score += 30

            if score > 0:
                scored_matches.append((score, hwnd))

            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.debug(f"EnumWindows error in find_windows: {e}")

        # Sort by match score descending
        scored_matches.sort(key=lambda item: item[0], reverse=True)
        return [hwnd for _, hwnd in scored_matches]

    def focus_window(self, title_or_handle: str | int) -> bool:
        """Bring target window to foreground."""
        self.safety.assert_not_aborted()
        if sys.platform != "win32":
            return False

        try:
            import win32con
            import win32gui

            hwnds = self.find_windows(title_or_handle)
            if not hwnds:
                return False

            hwnd = hwnds[0]
            if win32gui.IsWindow(hwnd):
                # Restore if minimized
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                return True
        except Exception as e:
            logger.debug(f"Error focusing window '{title_or_handle}': {e}")
        return False

    def close_window(self, title_or_handle: str | int, force: bool = False) -> bool:
        """Close target application window gracefully or terminate its process if force=True."""
        self.safety.assert_not_aborted()
        if sys.platform != "win32":
            return False

        try:
            import psutil
            import win32con
            import win32gui
            import win32process

            hwnds = self.find_windows(title_or_handle)
            if not hwnds:
                # If force=True, check if we can terminate directly by process name
                if force and isinstance(title_or_handle, str) and title_or_handle.strip():
                    target_proc = title_or_handle.strip().lower()
                    proc_candidates = [target_proc, f"{target_proc}.exe"]
                    killed = False
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            if proc.info["name"] and proc.info["name"].lower() in proc_candidates:
                                proc.kill()
                                killed = True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    return killed
                return False

            success = False
            for hwnd in hwnds:
                if not win32gui.IsWindow(hwnd):
                    continue

                if force:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid:
                        try:
                            psutil.Process(pid).kill()
                            success = True
                        except Exception:
                            pass
                else:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    success = True

            return success
        except Exception as e:
            logger.debug(f"Error closing window '{title_or_handle}': {e}")
            return False

    def maximize_window(self, title_or_handle: str | int | None = None) -> bool:
        """Maximize the specified window or the active window."""
        if sys.platform != "win32":
            return False
        try:
            import win32con
            import win32gui

            hwnd = None
            if title_or_handle is not None:
                hwnds = self.find_windows(title_or_handle)
                hwnd = hwnds[0] if hwnds else None
            else:
                hwnd = win32gui.GetForegroundWindow()

            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return True
        except Exception as e:
            logger.debug(f"Error maximizing window: {e}")
        return False

    def minimize_window(self, title_or_handle: str | int | None = None) -> bool:
        """Minimize the specified window or the active window."""
        if sys.platform != "win32":
            return False
        try:
            import win32con
            import win32gui

            hwnd = None
            if title_or_handle is not None:
                hwnds = self.find_windows(title_or_handle)
                hwnd = hwnds[0] if hwnds else None
            else:
                hwnd = win32gui.GetForegroundWindow()

            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return True
        except Exception as e:
            logger.debug(f"Error minimizing window: {e}")
        return False

    def snap_window(self, direction: str = "left", title_or_handle: str | int | None = None) -> bool:
        """Snap window to left/right/up using Windows Snap hotkeys."""
        if title_or_handle is not None:
            if not self.focus_window(title_or_handle):
                return False

        dir_clean = direction.strip().lower()
        if dir_clean in ("left", "west"):
            self.press_hotkey("win", "left")
        elif dir_clean in ("right", "east"):
            self.press_hotkey("win", "right")
        elif dir_clean in ("up", "top", "maximize"):
            self.press_hotkey("win", "up")
        elif dir_clean in ("down", "bottom", "minimize"):
            self.press_hotkey("win", "down")
        else:
            return False
        return True

    # ─── App Management ─────────────────────────────────────────

    def open_url(self, url: str, browser: str = "default") -> bool:
        """Open URL in default or specific browser reliably using Windows ShellExecute, start command, and browser launchers."""
        self.safety.assert_not_aborted()
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://", "ftp://", "file://", "ms-settings:", "mailto:", "spotify:")):
            clean_url = f"https://{clean_url}"

        browser_clean = browser.strip().lower()

        # If a specific browser is requested (e.g. 'chrome', 'edge', 'brave', 'firefox')
        if browser_clean not in ("default", ""):
            try:
                subprocess.Popen(["cmd.exe", "/c", "start", browser_clean, clean_url], shell=True)
                return True
            except Exception as e:
                logger.debug(f"start {browser_clean} failed: {e}")

        # Native Windows ShellExecute for default browser
        if sys.platform == "win32":
            try:
                os.startfile(clean_url)
                return True
            except Exception as e:
                logger.debug(f"os.startfile failed: {e}")
                try:
                    subprocess.Popen(["cmd.exe", "/c", "start", "", clean_url], shell=True)
                    return True
                except Exception as e2:
                    logger.debug(f"cmd start fallback failed: {e2}")

        # Fallback to webbrowser module
        try:
            import webbrowser
            return webbrowser.open(clean_url)
        except Exception:
            return False

    def resolve_executable(self, target: str) -> str | None:
        """Dynamically resolve application executable path using PATH, Registry App Paths, and Start Menu shortcuts."""
        if not target or sys.platform != "win32":
            return None

        clean_name = target.strip()
        lower_name = clean_name.lower()

        # If already an existing valid absolute path
        if os.path.isabs(clean_name) and os.path.exists(clean_name):
            return clean_name

        candidates = [clean_name]
        if not clean_name.endswith((".exe", ".cmd", ".bat")):
            candidates.extend([f"{clean_name}.exe", f"{clean_name}.cmd", f"{clean_name}.bat"])

        # 1. Dynamically search system PATH via shutil.which
        for cand in candidates:
            p = shutil.which(cand)
            if p and os.path.exists(p):
                return p

        # 2. Dynamically search Windows Registry App Paths (HKLM & HKCU)
        if winreg:
            for cand in candidates:
                for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{cand}"
                        with winreg.OpenKey(root, key_path) as key:
                            val, _ = winreg.QueryValueEx(key, "")
                            if isinstance(val, str) and val:
                                cleaned_val = val.strip().strip('"')
                                if os.path.exists(cleaned_val):
                                    return cleaned_val
                    except Exception:
                        pass

        # 3. Dynamically search Start Menu Programs, WindowsApps, and local application directories
        search_roots = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps"),
        ]

        target_base = os.path.splitext(lower_name)[0]
        for root_dir in search_roots:
            if not os.path.exists(root_dir):
                continue
            for dirpath, _, filenames in os.walk(root_dir):
                for f in filenames:
                    stem = os.path.splitext(f)[0].lower()
                    if target_base == stem or target_base in stem:
                        full_p = os.path.join(dirpath, f)
                        if os.path.exists(full_p):
                            return full_p

        return None

    def launch_app(self, app_name_or_path: str, args: list[str] | None = None) -> str:
        """Launch desktop application by name, URL, or executable path dynamically."""
        self.safety.assert_not_aborted()
        clean_target = app_name_or_path.strip()

        # URLs or protocol schemes
        if clean_target.startswith(("http://", "https://", "ms-settings:", "mailto:", "spotify:", "vscode:", "calc:", "bing:")):
            ok = self.open_url(clean_target)
            if ok:
                return f"Successfully opened URI/protocol: '{clean_target}'"
            return f"Failed to open URI '{clean_target}'"

        # Dynamically resolve executable path
        resolved_path = self.resolve_executable(clean_target)
        exec_target = resolved_path if resolved_path else clean_target

        # Standard Windows startfile or cmd start or subprocess
        try:
            if args:
                subprocess.Popen(["cmd.exe", "/c", "start", "", exec_target, *args], shell=True)
            else:
                try:
                    os.startfile(exec_target)
                except Exception:
                    subprocess.Popen(["cmd.exe", "/c", "start", "", exec_target], shell=True)
            return f"Launched application: '{exec_target}'"
        except Exception as e:
            return f"Failed to launch '{app_name_or_path}': {e}"

    # ─── Audio & System Settings ────────────────────────────────

    def set_master_volume(self, percent: int) -> int:
        """Set Windows master audio volume (0-100%)."""
        target_pct = max(0, min(100, percent))
        try:
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            except ImportError:
                from pycaw.pycaw import IAudioEndpointVolume  # type: ignore[no-redef]
                from pycaw.utils import AudioUtilities  # type: ignore[no-redef]

            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume: Any = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
            return target_pct
        except Exception as e:
            logger.debug(f"pycaw volume control failed: {e}")
            return -1

    def get_master_volume(self) -> int:
        """Get Windows master audio volume percentage (0-100%)."""
        try:
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            except ImportError:
                from pycaw.pycaw import IAudioEndpointVolume  # type: ignore[no-redef]
                from pycaw.utils import AudioUtilities  # type: ignore[no-redef]

            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume: Any = cast(interface, POINTER(IAudioEndpointVolume))
            scalar = volume.GetMasterVolumeLevelScalar()
            return round(scalar * 100)
        except Exception as e:
            logger.debug(f"pycaw get volume failed: {e}")
            return -1

    def mute_master_volume(self, mute: bool | None = None) -> bool:
        """Mute/unmute master audio, or toggle mute if mute is None."""
        try:
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            except ImportError:
                from pycaw.pycaw import IAudioEndpointVolume  # type: ignore[no-redef]
                from pycaw.utils import AudioUtilities  # type: ignore[no-redef]

            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume: Any = cast(interface, POINTER(IAudioEndpointVolume))

            is_muted = bool(volume.GetMute())
            target_mute = (not is_muted) if mute is None else mute
            volume.SetMute(int(target_mute), None)
            return target_mute
        except Exception:
            # Fallback to VK_VOLUME_MUTE virtual keypress
            self.send_media_key("mute")
            return True

    def send_media_key(self, key_type: str) -> bool:
        """Send native Windows hardware media virtual key."""
        if sys.platform != "win32":
            return False

        key_map = {
            "play_pause": VK_MEDIA_PLAY_PAUSE,
            "play": VK_MEDIA_PLAY_PAUSE,
            "pause": VK_MEDIA_PLAY_PAUSE,
            "next": VK_MEDIA_NEXT_TRACK,
            "next_track": VK_MEDIA_NEXT_TRACK,
            "prev": VK_MEDIA_PREV_TRACK,
            "prev_track": VK_MEDIA_PREV_TRACK,
            "previous": VK_MEDIA_PREV_TRACK,
            "stop": VK_MEDIA_STOP,
            "mute": VK_VOLUME_MUTE,
            "volup": VK_VOLUME_UP,
            "voldown": VK_VOLUME_DOWN,
        }

        vk = key_map.get(key_type.strip().lower())
        if vk is None:
            return False

        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
            return True
        except Exception as e:
            logger.debug(f"Error sending media key: {e}")
            return False

    def send_toast_notification(self, title: str, message: str) -> None:
        """Send native Windows 10/11 toast notification."""
        try:
            # Try powershell toast
            ps_cmd = (
                f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; '
                f'$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); '
                f'$textNodes = $template.GetElementsByTagName("text"); '
                f'$textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null; '
                f'$textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null; '
                f'$toast = [Windows.UI.Notifications.ToastNotification]::new($template); '
                f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS").Show($toast);'
            )
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], shell=True)
        except Exception:
            pass

    def lock_workstation(self) -> bool:
        """Lock the Windows user session."""
        if sys.platform != "win32":
            return False
        try:
            return bool(ctypes.windll.user32.LockWorkStation() != 0)
        except Exception:
            return False
