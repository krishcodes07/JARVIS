"""
System Commands — Modular bot commands for system status, help, and initialization.
"""

from __future__ import annotations

from jarvis.connectors.commands.models import BaseCommand, CommandContext


class StartCommand(BaseCommand):
    """Command to introduce JARVIS and display initial welcome message."""

    name: str = "start"
    aliases: list[str] = []
    description: str = "Start interacting with JARVIS."
    usage: str = "/start"
    category: str = "System"

    async def execute(self, ctx: CommandContext) -> str:
        """Render welcome start message."""
        active_model = ctx.engine.last_used_model
        active_session = ctx.connector.get_session_id(ctx.chat_id)
        persona_name = ctx.engine.config.jarvis.persona.title() if ctx.engine.config else "JARVIS"

        return (
            f"⚡ **Greetings! I am Jarvis.**\n\n"
            f"Your personal AI assistant is online and ready.\n\n"
            f"• **Active Model:** `{active_model}`\n"
            f"• **Session ID:** `{active_session}`\n\n"
            f"Type your query directly to start chatting, or type `/help` to view available commands."
        )


class HelpCommand(BaseCommand):
    """Command to display dynamic documentation of all registered bot commands."""

    name: str = "help"
    aliases: list[str] = ["h", "commands"]
    description: str = "Show list of available commands and usage instructions."
    usage: str = "/help"
    category: str = "System"

    async def execute(self, ctx: CommandContext) -> str:
        """Render dynamic help documentation grouped by category."""
        registry = getattr(ctx.connector, "commands", None)
        if not registry:
            return "⚠️ Command registry not available."

        commands_by_cat: dict[str, list[BaseCommand]] = {}
        for cmd in registry.list_commands():
            cat = cmd.category or "General"
            commands_by_cat.setdefault(cat, []).append(cmd)

        lines = ["🤖 **JARVIS Bot Commands**\n"]

        for category, cmd_list in sorted(commands_by_cat.items()):
            lines.append(f"📁 **{category} Commands**:")
            for cmd in cmd_list:
                aliases_str = f" *(aliases: {', '.join('/' + a for a in cmd.aliases)})*" if cmd.aliases else ""
                lines.append(f"• `/{cmd.name}` — {cmd.description}{aliases_str}")
                if cmd.usage and cmd.usage != f"/{cmd.name}":
                    lines.append(f"   Usage: `{cmd.usage}`")
            lines.append("")

        lines.append(
            "💡 *Tip: You can send any regular prompt to chat with JARVIS and invoke tools/skills!*"
        )
        return "\n".join(lines)


class StatusCommand(BaseCommand):
    """Command to check JARVIS engine health, active provider/model, tools, and session info."""

    name: str = "status"
    aliases: list[str] = ["info"]
    description: str = "View JARVIS status, active provider, model, and memory state."
    usage: str = "/status"
    category: str = "System"

    async def execute(self, ctx: CommandContext) -> str:
        """Render system status report."""
        config = ctx.engine.config
        provider_name = config.provider.active if config else "Unknown"
        model_name = ctx.engine.last_used_model
        tools_count = len(ctx.engine.tool_registry) if ctx.engine.tool_registry else 0
        active_session = ctx.connector.get_session_id(ctx.chat_id)

        mcp_servers: list[str] = []
        if ctx.engine.mcp_manager and hasattr(ctx.engine.mcp_manager, "_servers"):
            mcp_servers = list(ctx.engine.mcp_manager._servers.keys())

        mcp_info = ", ".join(f"`{s}`" for s in mcp_servers) if mcp_servers else "None"

        return (
            "📊 **JARVIS Engine Status**\n\n"
            f"• **Status:** `Online & Operational`\n"
            f"• **Provider:** `{provider_name}`\n"
            f"• **Model:** `{model_name}`\n"
            f"• **Active Session:** `{active_session}`\n"
            f"• **Loaded Tools:** `{tools_count}` tools\n"
            f"• **MCP Servers:** {mcp_info}\n"
            f"• **Platform Bridge:** `{ctx.connector.name.title()}`"
        )
