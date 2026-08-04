"""
Config template for creating new MCP servers.
"""

import os
from typing import List


def validate() -> List[str]:
    """Validate server environment variables and options."""
    errors = []
    # Add validation checks here if required:
    # if not os.environ.get("MY_API_KEY"):
    #     errors.append("MY_API_KEY environment variable is required.")
    return errors
