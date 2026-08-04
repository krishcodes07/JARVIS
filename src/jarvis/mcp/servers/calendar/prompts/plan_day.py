"""
Prompt workflow for daily planning.
"""

NAME = "Plan My Day"
DESCRIPTION = "Workflow prompt to review upcoming calendar events and build a structured daily plan."
TEMPLATE = """Please review my calendar resource (calendar://upcoming) and build a structured daily plan:

1. **Priority Events**: Meetings or deadlines that must not be missed.
2. **Focus Blocks**: Suggest times for deep work around my events.
3. **Buffer Time**: Flag potential conflicts or tight transitions between events.
4. **Action Items**: Prepare anything needed ahead of each event.

Keep the plan concise and actionable."""

ARGUMENTS = [
    {
        "name": "focus",
        "description": "Optional focus area to optimize the plan around (e.g. 'deep work', 'errands')",
        "required": False,
    }
]


def get_prompt(focus: str = "") -> str:
    """Generate the formatted prompt for daily planning."""
    if focus.strip():
        return TEMPLATE + f"\n\nOptimize the plan around: {focus.strip()}."
    return TEMPLATE
