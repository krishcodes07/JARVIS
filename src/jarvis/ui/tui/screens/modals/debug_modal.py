"""
Debug Modal Screen — Displays engine diagnostic information (/debug).
"""

from __future__ import annotations

import os
import platform
import sys
from typing import TYPE_CHECKING

from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine


class DebugModal(ModalScreen[None]):
    """Modal displaying real-time engine diagnostics and component states."""

    DEFAULT_CSS = """
    DebugModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #debug-card {
        width: 76;
        height: 80%;
        max-height: 80%;
        background: $surface;
        padding: 1 2;
    }

    #debug-card .title-bar {
        height: 1;
        layout: horizontal;
    }

    #debug-card .title-text {
        width: 1fr;
        text-style: bold;
        color: #ffffff;
    }

    #debug-card .esc-hint {
        width: auto;
        color: #737373;
    }

    #debug-scroll {
        height: 1fr;
        margin-top: 1;
        background: transparent;
        scrollbar-size: 0 0;
    }

    #debug-scroll Static {
        width: 100%;
    }

    #debug-footer {
        height: 1;
        margin-top: 1;
        color: #737373;
        text-align: center;
        width: 100%;
    }
    """

    def __init__(
        self,
        engine: JarvisEngine | None = None,
        is_generating: bool = False,
        is_voice_active: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.is_generating = is_generating
        self.is_voice_active = is_voice_active

    def compose(self):
        with Vertical(id="debug-card"):
            with Horizontal(classes="title-bar"):
                yield Static("Engine Debug Information", classes="title-text")
                yield Static("esc", classes="esc-hint")
            with VerticalScroll(id="debug-scroll"):
                yield Static(self._build_debug_text())
            yield Static("Esc / Enter close", id="debug-footer")

    def _build_debug_text(self) -> Text:
        """Build full diagnostic text."""
        txt = Text()

        # ── System Environment ──
        txt.append("System Environment\n", style="bold #60a5fa")
        self._add_row(txt, "OS", f"{platform.system()} {platform.release()} ({platform.machine()})", "#94a3b8")
        self._add_row(txt, "Python Version", sys.version.split()[0], "#94a3b8")
        self._add_row(txt, "PID", str(os.getpid()), "#94a3b8")
        self._add_row(txt, "Working Dir", os.getcwd(), "#60a5fa")

        # ── Runtime & Engine State ──
        txt.append("\nRuntime & Engine State\n", style="bold #60a5fa")
        if not self.engine:
            self._add_row(txt, "Engine Status", "Disconnected / Mock", "#ef4444")
            self._add_row(txt, "Generating Output", "Yes" if self.is_generating else "No", "#fbbf24" if self.is_generating else "#737373")
            self._add_row(txt, "Voice Subsystem", "Listening..." if self.is_voice_active else "Idle", "#ef4444" if self.is_voice_active else "#737373")
            return txt

        session_id = self.engine.session.session_id if self.engine.session else "N/A"
        messages_cnt = len(self.engine.session.messages) if (self.engine.session and hasattr(self.engine.session, "messages")) else 0
        c = self.engine.config

        self._add_row(txt, "Engine Status", "Initialized & Running", "#22c55e")
        self._add_row(txt, "Session ID", session_id, "#60a5fa")
        self._add_row(txt, "Session Messages", str(messages_cnt), "#a78bfa")
        self._add_row(txt, "Generating Output", "Yes" if self.is_generating else "No", "#fbbf24" if self.is_generating else "#737373")
        self._add_row(txt, "Voice Mode", "Listening..." if self.is_voice_active else "Idle / Off", "#ef4444" if self.is_voice_active else "#737373")

        # ── LLM Provider ──
        txt.append("\nLLM Provider Manager\n", style="bold #60a5fa")
        if c:
            self._add_row(txt, "Active Provider", c.provider.active.upper(), "#3b82f6")
            self._add_row(txt, "Active Model", c.provider.model, "#60a5fa")
            self._add_row(txt, "Thinking Enabled", "Yes" if c.provider.thinking else "No", "#22c55e" if c.provider.thinking else "#ef4444")
            if c.provider.reasoning_effort:
                self._add_row(txt, "Reasoning Effort", c.provider.reasoning_effort, "#a78bfa")
            last_used = getattr(self.engine.provider_manager, "last_used_model", None) if hasattr(self.engine, "provider_manager") else None
            if last_used:
                self._add_row(txt, "Last Response Model", last_used, "#f59e0b")
            fb = c.provider.fallback
            if fb.enabled:
                self._add_row(txt, "Fallback Target", f"{fb.provider} ({fb.model})", "#f97316")


        # ── Tools & MCP ──
        txt.append("\nTools & MCP Status\n", style="bold #60a5fa")
        tools_cnt = len(self.engine.tool_registry) if self.engine.tool_registry else 0
        self._add_row(txt, "Registered Tools", f"{tools_cnt} tools active", "#22c55e")

        if self.engine.mcp_manager:
            connections = getattr(self.engine.mcp_manager, "servers", {})
            conn_cnt = len(connections) if isinstance(connections, dict) else 0
            self._add_row(txt, "MCP Servers", f"{conn_cnt} servers configured", "#10b981")

        # ── Memory Subsystem ──
        txt.append("\nMemory Subsystem\n", style="bold #60a5fa")
        if hasattr(self.engine, "memory_manager") and self.engine.memory_manager:
            self._add_row(txt, "Memory Manager", "Active", "#22c55e")
        else:
            self._add_row(txt, "Memory Manager", "Loaded", "#94a3b8")

        return txt

    @staticmethod
    def _add_row(txt: Text, label: str, value: str, color: str) -> None:
        """Append formatted label-value line."""
        txt.append(f"    {label:<24}", style="bold #cbd5e1")
        txt.append(f"{value}\n", style=f"bold {color}")

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_enter(self) -> None:
        self.dismiss(None)
