"""
JARVIS Dev Runner — Quick development launcher.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    """Run JARVIS in development mode with debug logging."""
    subprocess.run(
        [sys.executable, "-m", "jarvis", "--debug"],
        cwd=PROJECT_ROOT,
    )


if __name__ == "__main__":
    main()
