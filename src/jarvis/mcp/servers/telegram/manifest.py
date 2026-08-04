"""
Manifest for Telegram User Account MCP Server Package (MTProto).
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="telegram",
    version="1.0.0",
    description="Telegram User Account MCP Server using Telethon MTProto to send and read messages directly from your personal Telegram account.",
    author="MCP Platform Team",
    homepage="https://github.com/modelcontextprotocol",
    required_env_vars=["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING"],
    capabilities=["tools", "resources", "prompts"],
    dependencies=["telethon"],
    enabled_by_default=True,
    category="communication",
)

