"""
JARVIS Setup — first-run onboarding.

Exposes the interactive wizard and the live validation helpers it uses, so other
entry points (``python main.py --setup``, ``python setup.py``, the TUI) can reuse
the same verified configuration flow.
"""

from __future__ import annotations

from jarvis.setup.validation import (
    CheckResult,
    check_api_key,
    check_embedding,
    check_extraction_model,
    check_local_embedding,
)
from jarvis.setup.wizard import run_setup_wizard

__all__ = [
    "CheckResult",
    "check_api_key",
    "check_embedding",
    "check_extraction_model",
    "check_local_embedding",
    "run_setup_wizard",
]
