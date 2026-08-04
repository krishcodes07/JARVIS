"""
Excel Active Workbooks Resource loader.
Exposes excel://workbooks
"""

import os
from ..config import WORK_DIR

URI = "excel://workbooks"
NAME = "Excel Workbooks Directory"
DESCRIPTION = "List of all Excel spreadsheet workbooks (.xlsx) available in the working directory."
MIME_TYPE = "text/plain"


def workbooks() -> str:
    """Discover available Excel workbooks."""
    try:
        if not os.path.exists(WORK_DIR):
            return f"Directory {WORK_DIR} does not exist."

        files = [f for f in os.listdir(WORK_DIR) if f.endswith((".xlsx", ".xlsm"))]
        if not files:
            return f"No Excel workbooks found in '{WORK_DIR}'."

        lines = [f"📊 Available Excel Workbooks in '{WORK_DIR}':"]
        for file in sorted(files):
            full_path = os.path.join(WORK_DIR, file)
            size = os.path.getsize(full_path)
            lines.append(f"  📄 {file} ({size:,} bytes)")

        return "\n".join(lines)
    except Exception as e:
        return f"Error loading Excel workbooks: {e}"
