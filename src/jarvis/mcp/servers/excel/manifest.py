"""
Manifest for Excel MCP Server Package.
"""

from jarvis.mcp.platform.models import ServerManifest

MANIFEST = ServerManifest(
    name="excel",
    version="1.0.0",
    description=(
        "Excel MCP Server providing spreadsheet manipulation tools, "
        "active workbooks resource, and report prompts."
    ),
    author="MCP Platform Team",
    homepage="https://openpyxl.readthedocs.io",
    required_env_vars=[],
    capabilities=["tools", "resources", "prompts"],
    dependencies=["openpyxl"],
    enabled_by_default=True,
    category="productivity",
)

