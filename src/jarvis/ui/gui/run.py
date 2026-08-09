"""Convenient development launcher for the JARVIS GUI."""

from pathlib import Path
import sys

# Add repository root src/ to sys.path
GUI_ROOT = Path(__file__).resolve().parent
REPO_SRC = GUI_ROOT.parents[2]

if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from jarvis.ui.gui.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
