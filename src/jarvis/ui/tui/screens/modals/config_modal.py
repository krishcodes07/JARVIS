"""
Config Modal Screen — Interactive dialog displaying active JARVIS settings (/config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine


class ConfigModal(ModalScreen[None]):
    """Modal displaying formatted configuration status."""

    DEFAULT_CSS = """
    ConfigModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #config-card {
        width: 72;
        height: 80%;
        max-height: 80%;
        background: $surface;
        padding: 1 2;
    }

    #config-card .title-bar {
        height: 1;
        layout: horizontal;
    }

    #config-card .title-text {
        width: 1fr;
        text-style: bold;
        color: #ffffff;
    }

    #config-card .esc-hint {
        width: auto;
        color: #737373;
    }

    #config-scroll {
        height: 1fr;
        margin-top: 1;
        background: transparent;
        scrollbar-size: 0 0;
    }

    #config-scroll Static {
        width: 100%;
    }

    #config-footer {
        height: 1;
        margin-top: 1;
        color: #737373;
        text-align: center;
        width: 100%;
    }
    """

    def __init__(self, engine: "JarvisEngine | None" = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.engine = engine

    def compose(self):
        with Vertical(id="config-card"):
            with Horizontal(classes="title-bar"):
                yield Static("JARVIS Configuration", classes="title-text")
                yield Static("esc", classes="esc-hint")
            with VerticalScroll(id="config-scroll"):
                yield Static(self._build_config_text())
            yield Static("Esc / Enter close", id="config-footer")

    def _build_config_text(self) -> Text:
        """Build the full config content."""
        txt = Text()

        if not self.engine or not self.engine.config:
            txt.append("  No active engine configuration found.", style="dim #ef4444")
            return txt

        c = self.engine.config

        # ── Provider & Model ──
        txt.append("Provider & Model\n", style="bold #60a5fa")
        self._add_row(txt, "LLM Provider", c.provider.active.upper(), "#3b82f6")
        self._add_row(txt, "Active Model", c.provider.model, "#60a5fa")
        self._add_row(txt, "Temperature", str(c.provider.temperature), "#a78bfa")
        self._add_row(txt, "Max Tokens", str(c.provider.max_tokens), "#a78bfa")
        self._add_row(txt, "Top P", str(c.provider.top_p), "#a78bfa")

        # ── Fallback ──
        fb = c.provider.fallback
        txt.append("\nFallback Configuration\n", style="bold #60a5fa")
        fb_status = "Enabled" if fb.enabled else "Disabled"
        fb_color = "#22c55e" if fb.enabled else "#737373"
        self._add_row(txt, "Fallback", fb_status, fb_color)
        if fb.enabled:
            self._add_row(txt, "Fallback Provider", fb.provider, "#f97316")
            self._add_row(txt, "Fallback Model", fb.model, "#f97316")

        # ── Memory ──
        txt.append("\nMemory System\n", style="bold #60a5fa")
        conv = c.memory.conversation
        conv_status = "Enabled" if conv.enabled else "Disabled"
        self._add_row(txt, "Conversation", conv_status, "#22c55e" if conv.enabled else "#737373")
        if conv.enabled:
            self._add_row(txt, "  Backend", conv.backend, "#94a3b8")
            self._add_row(txt, "  Max Messages", str(conv.max_messages), "#94a3b8")

        lt = c.memory.long_term
        lt_status = "Enabled" if lt.enabled else "Disabled"
        self._add_row(txt, "Long-Term", lt_status, "#22c55e" if lt.enabled else "#737373")

        vec = c.memory.vector
        vec_status = "Enabled" if vec.enabled else "Disabled"
        self._add_row(txt, "Vector Memory", vec_status, "#22c55e" if vec.enabled else "#737373")
        if vec.enabled:
            self._add_row(txt, "  Embedding", f"{vec.embedding_provider}/{vec.embedding_model}", "#94a3b8")

        # ── Tools ──
        txt.append("\nTools & MCP\n", style="bold #60a5fa")
        tools_status = "Enabled" if getattr(c.tools, "enabled", False) else "Disabled"
        self._add_row(txt, "Tools System", tools_status, "#22c55e" if c.tools.enabled else "#737373")
        if c.tools.enabled:
            self._add_row(txt, "  Auto Approve", "Yes" if c.tools.auto_approve else "No", "#94a3b8")
            self._add_row(txt, "  Max Turns", str(c.tools.max_turns), "#94a3b8")
            self._add_row(txt, "  Timeout", f"{c.tools.timeout}s", "#94a3b8")

        mcp_status = "Enabled" if getattr(c.mcp, "enabled", False) else "Disabled"
        self._add_row(txt, "MCP Integration", mcp_status, "#22c55e" if c.mcp.enabled else "#737373")

        # ── Voice ──
        txt.append("\nVoice System\n", style="bold #60a5fa")
        voice = c.voice
        voice_status = "Enabled" if voice.enabled else "Disabled"
        self._add_row(txt, "Voice", voice_status, "#22c55e" if voice.enabled else "#737373")
        self._add_row(txt, "Mode", voice.mode, "#94a3b8")
        self._add_row(txt, "TTS Provider", voice.tts.provider, "#94a3b8")
        self._add_row(txt, "TTS Voice", voice.tts.voice, "#94a3b8")
        self._add_row(txt, "STT Provider", voice.stt.provider, "#94a3b8")

        # ── UI ──
        txt.append("\nUI Settings\n", style="bold #60a5fa")
        self._add_row(txt, "Default UI", c.ui.default, "#94a3b8")
        self._add_row(txt, "Theme", c.ui.tui.theme, "#94a3b8")
        self._add_row(txt, "Show Tool Output", "Yes" if c.ui.tui.show_tool_output else "No", "#94a3b8")
        self._add_row(txt, "Show Thinking", "Yes" if c.ui.tui.show_thinking else "No", "#94a3b8")

        return txt

    @staticmethod
    def _add_row(txt: Text, label: str, value: str, color: str) -> None:
        """Append a formatted key-value row."""
        txt.append(f"    {label:<22}", style="bold #cbd5e1")
        txt.append(f"{value}\n", style=f"bold {color}")

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_enter(self) -> None:
        self.dismiss(None)
