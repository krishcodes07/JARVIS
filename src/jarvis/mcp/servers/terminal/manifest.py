"""
Manifest for Terminal MCP Server Package.
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="terminal",
    version="1.0.0",
    description="Terminal MCP Server providing full terminal command execution, background task management, and system status resources.",
    author="MCP Platform Team",
    homepage="https://github.com/modelcontextprotocol",
    required_env_vars=[],
    capabilities=["tools", "resources", "prompts"],
    dependencies=[],
    enabled_by_default=True,
    category="system",
)

