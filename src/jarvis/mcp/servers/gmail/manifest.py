"""
Manifest for Gmail MCP Server Package.
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="gmail",
    version="1.0.0",
    description="Gmail MCP Server providing email tools, resources (inbox/drafts), and email workflow prompts.",
    author="MCP Platform Team",
    homepage="https://gmail.com",
    required_env_vars=["GMAIL_EMAIL", "GMAIL_APP_PASSWORD"],
    capabilities=["tools", "resources", "prompts"],
    dependencies=[],
    enabled_by_default=True,
    category="communication",
)

