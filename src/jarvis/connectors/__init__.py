"""
JARVIS Connectors — Multi-channel messaging bridges (Telegram, Discord, etc.).
"""

from jarvis.connectors.base import BaseConnector
from jarvis.connectors.commands import BaseCommand, CommandContext, CommandRegistry
from jarvis.connectors.manager import ConnectorManager
from jarvis.connectors.models import ConnectorStatus, InboundMessage, OutboundMessage
from jarvis.connectors.runner import run_connector_service
from jarvis.connectors.telegram.connector import TelegramConnector

__all__ = [
    "BaseConnector",
    "BaseCommand",
    "CommandContext",
    "CommandRegistry",
    "ConnectorManager",
    "InboundMessage",
    "OutboundMessage",
    "ConnectorStatus",
    "TelegramConnector",
    "run_connector_service",
]
