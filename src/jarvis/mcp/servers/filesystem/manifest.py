"""
Manifest for Filesystem MCP Server Package.
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="filesystem",
    version="1.0.0",
    description=(
        "Filesystem MCP Server providing file/folder management tools, "
        "workspace resources, and analysis prompts."
    ),
    author="MCP Platform Team",
    homepage="https://github.com/modelcontextprotocol",
    required_env_vars=[],
    capabilities=["tools", "resources", "prompts"],
    dependencies=[],
    enabled_by_default=True,
    category="system",
)

