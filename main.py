"""
JARVIS — Main Entry Point.

Usage:
    python main.py              # Run with default UI (TUI)
    python main.py --ui web     # Run Web UI
    python main.py --ui web --port 8080  # Run Web UI on custom port
    python main.py --ui gui     # Run Desktop GUI
    python main.py --debug      # Run with debug logging

Or use the module entry point:
    python -m jarvis
"""

import sys
from pathlib import Path

# Add src/ to Python path so jarvis package is importable when running directly
_src_dir = str(Path(__file__).resolve().parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from jarvis.__main__ import main

if __name__ == "__main__":
    main()
