"""
Configuration and safety checks for Excel MCP server.
"""

import os

WORK_DIR = os.environ.get("EXCEL_WORK_DIR", "").strip()


def safe_excel_path(filename: str) -> str:
    """Resolve and validate an Excel file path across any drive or relative directory."""
    if not filename.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        filename += ".xlsx"
    expanded = os.path.expanduser(filename)

    if os.path.isabs(expanded):
        resolved = os.path.realpath(expanded)
    else:
        base_dir = WORK_DIR if (WORK_DIR and WORK_DIR not in ("*", "ALL")) else os.getcwd()
        resolved = os.path.realpath(os.path.join(base_dir, expanded))

    return resolved


def validate() -> list[str]:
    errors = []
    if WORK_DIR and WORK_DIR not in ("*", "ALL", ""):
        if not os.path.exists(WORK_DIR):
            try:
                os.makedirs(WORK_DIR, exist_ok=True)
            except Exception as e:
                errors.append(f"EXCEL_WORK_DIR '{WORK_DIR}' does not exist and cannot be created: {e}")
    return errors
