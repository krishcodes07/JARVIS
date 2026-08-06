"""
Slash Command Definitions and Execution Logic for JARVIS TUI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlashCommand:
    name: str
    description: str
    usage: str = ""
    action: str = ""


# Registry of available slash commands for UI autocomplete and execution
COMMAND_REGISTRY: list[SlashCommand] = [
    SlashCommand("/sessions", "Manage & switch conversation sessions", "/sessions", "action_sessions"),
    SlashCommand("/models", "Switch active model or browse providers", "/models [provider]", "action_models"),
    SlashCommand("/provider", "Switch active LLM provider", "/provider <name>", "action_provider"),
    SlashCommand("/connect", "Connect model or API provider", "/connect <provider>", "action_connect"),
    SlashCommand("/clear", "Start a new conversation session", "/clear", "action_clear"),
    SlashCommand("/copy", "Copy last AI response to clipboard", "/copy", "action_copy"),
    SlashCommand("/config", "View current JARVIS configuration", "/config", "action_config"),
    SlashCommand("/mcp", "View MCP server status and connections", "/mcp", "action_mcps"),
    SlashCommand("/voice", "Toggle or set text/voice mode", "/voice [text|voice]", "action_voice"),
    SlashCommand("/stt", "Switch Speech-To-Text provider", "/stt <provider>", "action_stt"),
    SlashCommand("/tts", "Switch Text-To-Speech provider", "/tts <provider>", "action_tts"),
    SlashCommand("/voices", "List available TTS voices", "/voices", "action_voices"),
    SlashCommand("/debug", "View engine & system debug info", "/debug", "action_debug"),
    SlashCommand("/help", "Show help and commands overview", "/help", "action_help"),
    SlashCommand("/exit", "Exit the JARVIS application", "/exit", "action_exit"),
]


def filter_commands(query: str) -> list[SlashCommand]:
    """Filter registered slash commands matching search query.

    Args:
        query: Query string starting with '/' or partial command name.

    Returns:
        Filtered list of matching SlashCommand objects.
    """
    clean = query.strip().lower()
    if not clean.startswith("/"):
        clean = "/" + clean

    return [
        cmd for cmd in COMMAND_REGISTRY
        if cmd.name.lower().startswith(clean) or clean in cmd.description.lower()
    ]


def get_command(name: str) -> SlashCommand | None:
    """Find registered SlashCommand by exact name (case-insensitive)."""
    clean = name.strip().lower()
    if not clean.startswith("/"):
        clean = "/" + clean

    return next((cmd for cmd in COMMAND_REGISTRY if cmd.name.lower() == clean), None)

