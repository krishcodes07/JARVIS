"""
Manifest for Calendar MCP Server Package.
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="calendar",
    version="1.0.0",
    description="Calendar MCP Server providing event management tools, an upcoming events resource, and planning prompts.",
    author="JARVIS Team",
    homepage="",
    required_env_vars=[],
    capabilities=["tools", "resources", "prompts"],
    dependencies=[],
    enabled_by_default=True,
    category="productivity",
)
