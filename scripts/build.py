"""
JARVIS Build Script — Build the project for distribution.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    """Build the JARVIS package."""
    print("Building JARVIS...")
    subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=PROJECT_ROOT,
    )
    print("Build complete! Check dist/ for output.")


if __name__ == "__main__":
    main()
