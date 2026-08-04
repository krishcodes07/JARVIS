"""
Create workbook tool for Excel.
"""

from operator import imod
import os
import openpyxl
from ..config import safe_excel_path

NAME = "create_workbook"
DESCRIPTION = "Create a new Excel workbook with optional initial headers and sheet name."


def create_workbook(
    filename: str,
    sheet_name: str = "Sheet1",
    headers: list[str] | None = None,
) -> str:
    """
    Create a new Excel workbook.

    Args:
        filename: Name of the file (e.g. "budget.xlsx"). Saved in EXCEL_WORK_DIR.
        sheet_name: Name for the initial worksheet (default: Sheet1).
        headers: List of column header strings to add in the first row.

    Returns:
        Success or error message.
    """
    try:
        filepath = safe_excel_path(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        if ws is None:
            return "❌ Failed to initialize workbook: no active sheet."
        ws.title = sheet_name

        if headers:
            ws.append(headers)

        wb.save(filepath)
        return f"✅ Created workbook: {filepath} (sheet: '{sheet_name}')"

    except Exception as e:
        return f"❌ Error creating workbook: {e}"
