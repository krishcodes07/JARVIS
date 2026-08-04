"""
JARVIS Constants — Global constants and enums.
"""

from __future__ import annotations

from enum import StrEnum


# ─── Application ──────────────────────────────────────────────
APP_NAME = "JARVIS"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "The Ultimate AI Assistant"


# ─── Provider Protocols ──────────────────────────────────────
class Protocol(StrEnum):
    """Supported LLM API protocols."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


# ─── Message Roles ────────────────────────────────────────────
class Role(StrEnum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ─── Memory Types ─────────────────────────────────────────────
class MemoryType(StrEnum):
    """Types of memory storage."""
    CONVERSATION = "conversation"
    LONG_TERM = "long_term"
    VECTOR = "vector"


# ─── UI Types ─────────────────────────────────────────────────
class UIType(StrEnum):
    """Available user interface types."""
    TUI = "tui"
    WEB = "web"
    GUI = "gui"


# ─── Tool Categories ─────────────────────────────────────────
class ToolCategory(StrEnum):
    """Built-in tool categories."""
    BASIC = "basic"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    CODE = "code"


# ─── MCP Transport ───────────────────────────────────────────
class MCPTransport(StrEnum):
    """MCP server transport types."""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
