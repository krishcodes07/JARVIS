"""
Command Registry — Central registry and dispatcher for connector bot commands.
"""

from __future__ import annotations

import logging
import shlex
from typing import TYPE_CHECKING

from jarvis.connectors.commands.mcp_cmd import MCPCommand
from jarvis.connectors.commands.models import BaseCommand, CommandContext
from jarvis.connectors.commands.models_cmd import ModelCommand
from jarvis.connectors.commands.session import (
    ClearSessionCommand,
    NewSessionCommand,
    SessionCommand,
)
from jarvis.connectors.commands.system import (
    HelpCommand,
    StartCommand,
    StatusCommand,
)

if TYPE_CHECKING:
    from jarvis.connectors.base import BaseConnector
    from jarvis.connectors.models import InboundMessage
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Registry holding all bot commands with dispatching and argument parsing."""

    def __init__(self) -> None:
        self._commands: dict[str, BaseCommand] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: BaseCommand) -> None:
        """Register a command instance into the registry."""
        name = command.name.lower().lstrip("/")
        self._commands[name] = command

        for alias in command.aliases:
            clean_alias = alias.lower().lstrip("/")
            self._aliases[clean_alias] = name

    def unregister(self, name: str) -> None:
        """Unregister a command by name."""
        clean_name = name.lower().lstrip("/")
        cmd = self._commands.pop(clean_name, None)
        if cmd:
            for alias in cmd.aliases:
                self._aliases.pop(alias.lower().lstrip("/"), None)

    def get(self, name_or_alias: str) -> BaseCommand | None:
        """Retrieve a command by name or alias."""
        clean = name_or_alias.lower().lstrip("/")
        actual_name = self._aliases.get(clean, clean)
        return self._commands.get(actual_name)

    def list_commands(self) -> list[BaseCommand]:
        """Return all uniquely registered commands."""
        return list(self._commands.values())

    async def dispatch(
        self,
        inbound: InboundMessage,
        connector: BaseConnector,
        engine: JarvisEngine,
    ) -> str | None:
        """Parse incoming message and dispatch to registered command handler if matched.

        Returns:
            Formatted response string if command was executed, or None if not a command.
        """
        raw_text = inbound.text.strip()
        if not raw_text.startswith("/"):
            return None

        # Split command token and arguments
        parts = raw_text.split(maxsplit=1)
        cmd_token = parts[0][1:].lower()  # Remove leading slash

        # Strip bot mentions (e.g. /session@JarvisAiBot -> /session)
        if "@" in cmd_token:
            cmd_token = cmd_token.split("@")[0]

        command = self.get(cmd_token)
        if not command:
            return None

        raw_args = parts[1].strip() if len(parts) > 1 else ""
        try:
            args = shlex.split(raw_args) if raw_args else []
        except Exception:
            args = raw_args.split()

        ctx = CommandContext(
            connector=connector,
            inbound=inbound,
            engine=engine,
            command_name=cmd_token,
            args=args,
            raw_args=raw_args,
            chat_id=inbound.chat_id,
            user_id=inbound.user_id,
        )

        try:
            logger.info(f"[{connector.name}] Executing command: /{cmd_token} with args: {args}")
            return await command.execute(ctx)
        except Exception as e:
            logger.error(f"Error executing command /{cmd_token}: {e}", exc_info=True)
            return f"⚠️ **Error executing command `/{cmd_token}`**: {e}"

    @classmethod
    def create_default(cls) -> CommandRegistry:
        """Factory creating a registry populated with default system, session, model, and MCP commands."""
        registry = cls()
        registry.register(StartCommand())
        registry.register(HelpCommand())
        registry.register(StatusCommand())
        registry.register(SessionCommand())
        registry.register(NewSessionCommand())
        registry.register(ClearSessionCommand())
        registry.register(ModelCommand())
        registry.register(MCPCommand())
        return registry
