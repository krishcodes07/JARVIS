"""
Command Models — Context and BaseCommand classes for extensible connector bot commands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.connectors.base import BaseConnector
    from jarvis.connectors.models import InboundMessage
    from jarvis.core.engine import JarvisEngine


@dataclass
class CommandContext:
    """Context object provided to a command handler upon execution."""

    connector: BaseConnector
    inbound: InboundMessage
    engine: JarvisEngine
    command_name: str
    args: list[str] = field(default_factory=list)
    raw_args: str = ""
    chat_id: str = ""
    user_id: str = ""


class BaseCommand(ABC):
    """Abstract base class for all connector bot commands (e.g. /session, /model, /mcp)."""

    name: str
    aliases: list[str] = []
    description: str = ""
    usage: str = ""
    category: str = "General"

    @abstractmethod
    async def execute(self, ctx: CommandContext) -> str | None:
        """Execute the command and return a formatted markdown/text response.

        Args:
            ctx: Execution context containing connector, message, engine, and arguments.

        Returns:
            Response text string to reply with, or None if handled directly.
        """
        ...
