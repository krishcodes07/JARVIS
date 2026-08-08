"""
Manifest for Telegram User Account MCP Server Package (MTProto).
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="telegram",
    version="1.1.0",
    description=(
        "Telegram User Account MCP Server using Telethon MTProto. Allows sending/reading messages, "
        "sending photos & files, voice notes, message reactions, pinning/unpinning, forwarding messages, "
        "downloading media, listing group members, and creating group chats."
    ),
    author="MCP Platform Team",
    homepage="https://github.com/modelcontextprotocol",
    required_env_vars=["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING"],
    capabilities=["tools", "resources", "prompts"],
    dependencies=["telethon"],
    enabled_by_default=True,
    category="communication",
)

