"""
Get system info tool for Terminal MCP Server.
"""

import os
import platform
import sys

NAME = "get_system_info"
DESCRIPTION = "Retrieve operating system details, Python version, platform environment, and working directory."


def get_system_info() -> str:
    """
    Get system details.

    Returns:
        Formatted summary of system environment.
    """
    try:
        info = [
            "Terminal & System Environment Summary:",
            f"  • OS Platform: {platform.system()} {platform.release()} ({platform.machine()})",
            f"  • OS Version: {platform.version()}",
            f"  • Python Version: {sys.version.split()[0]} ({sys.executable})",
            f"  • Current Working Directory: {os.getcwd()}",
            f"  • User Account: {os.getenv('USERNAME', os.getenv('USER', 'Unknown'))}",
            f"  • CPU Cores: {os.cpu_count()}",
        ]
        return "\n".join(info)
    except Exception as e:
        return f"Error: Failed to get system info: {e}"
