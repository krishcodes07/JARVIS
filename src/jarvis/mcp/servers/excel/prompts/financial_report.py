"""
Prompt workflow for Excel financial report generation.
"""

NAME = "Generate Financial Report"
DESCRIPTION = "Workflow prompt to create a structured financial report spreadsheet."
TEMPLATE = """Please create a financial report workbook named '{report_name}.xlsx':

1. **Summary Sheet**: Revenue, Expenses, Net Income, Margins.
2. **Monthly Breakdown**: Month-by-month tables.
3. **Formulas**: Include automated SUM and AVERAGE formulas for column totals.

Ensure clean column headers and clear currency formatting."""

ARGUMENTS = [
    {"name": "report_name", "description": "Base filename for the report", "required": True}
]


def get_prompt(report_name: str = "Financial_Report_2026") -> str:
    return TEMPLATE.format(report_name=report_name)
