"""
JARVIS Exceptions — Custom exception hierarchy.

All JARVIS-specific exceptions inherit from JarvisError.
This allows consumers to catch `JarvisError` for any JARVIS-related failure.
"""

from __future__ import annotations


class JarvisError(Exception):
    """Base exception for all JARVIS errors."""

    def __init__(self, message: str = "", *args: object) -> None:
        self.message = message
        super().__init__(message, *args)


# ─── Core Errors ──────────────────────────────────────────────

class ConfigError(JarvisError):
    """Configuration loading or validation error."""


class InitializationError(JarvisError):
    """Subsystem initialization failure."""


# ─── Provider Errors ──────────────────────────────────────────

class ProviderError(JarvisError):
    """Base error for provider-related failures."""


class ProviderNotFoundError(ProviderError):
    """Requested provider is not registered."""


class ProviderAuthError(ProviderError):
    """Authentication failure (invalid or missing API key)."""


class ModelNotFoundError(ProviderError):
    """Requested model is not available for the provider."""


class RateLimitError(ProviderError):
    """API rate limit exceeded."""


class TokenLimitError(ProviderError):
    """Request exceeds the model's token limit."""


# ─── Memory Errors ────────────────────────────────────────────

class MemoryError(JarvisError):
    """Base error for memory subsystem failures."""


class ConversationNotFoundError(MemoryError):
    """Requested conversation does not exist."""


class VectorStoreError(MemoryError):
    """Vector store operation failure."""


# ─── Tool Errors ──────────────────────────────────────────────

class ToolError(JarvisError):
    """Base error for tool execution failures."""


class ToolNotFoundError(ToolError):
    """Requested tool is not registered."""


class ToolExecutionError(ToolError):
    """Tool execution failed."""


class ToolTimeoutError(ToolError):
    """Tool execution timed out."""


class ToolPermissionError(ToolError):
    """Tool execution denied (user did not approve)."""


# ─── MCP Errors ───────────────────────────────────────────────

class MCPError(JarvisError):
    """Base error for MCP-related failures."""


class MCPConnectionError(MCPError):
    """Failed to connect to an MCP server."""


class MCPServerNotFoundError(MCPError):
    """Requested MCP server is not registered."""


class MCPToolError(MCPError):
    """MCP tool execution failure."""


# ─── Voice Errors ─────────────────────────────────────────────

class VoiceError(JarvisError):
    """Base error for voice (TTS/STT) failures."""


class VoiceConfigError(VoiceError):
    """Invalid voice configuration."""


class VoiceAuthError(VoiceError):
    """Voice provider authentication failure (e.g. missing API key)."""


class VoiceProviderError(VoiceError):
    """Voice provider request or processing failure."""


class VoiceAudioError(VoiceError):
    """Audio device, playback, or capture failure."""


# ─── Skill Errors ─────────────────────────────────────────────

class SkillError(JarvisError):
    """Base error for skill-related failures."""


class SkillNotFoundError(SkillError):
    """Requested skill does not exist."""


class SkillLoadError(SkillError):
    """Failed to load or parse a skill definition."""
