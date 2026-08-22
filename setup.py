"""
JARVIS Setup Entry Point.

Usage:
    python setup.py
"""

import asyncio
import sys
from pathlib import Path

# Add src/ to sys.path
_src_dir = str(Path(__file__).resolve().parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from jarvis.setup.wizard import run_setup_wizard

if __name__ == "__main__":
    try:
        asyncio.run(run_setup_wizard())
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(0)
