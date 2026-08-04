"""
Calendar MCP Server Entrypoint — built dynamically by the JARVIS MCP platform.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from jarvis.mcp.platform.runner import create_server_from_package

mcp = create_server_from_package(__file__)

if __name__ == "__main__":
    mcp.run()
