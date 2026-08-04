"""
Manifest template for creating new MCP servers.
Copy this folder to create a new server (e.g. mcp_servers/slack/).
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="my_server",
    version="1.0.0",
    description="Describe what your MCP server does here.",
    author="Your Name",
    homepage="https://example.com",
    required_env_vars=[],
    capabilities=["tools", "resources", "prompts"],
    dependencies=[],
    enabled_by_default=True,
    category="custom",
)

