"""
Prompt workflow for executing terminal automation scripts.
"""

NAME = "Execute Terminal Script"
DESCRIPTION = "Workflow prompt template for writing and running automated terminal scripts."
TEMPLATE = """Execute the following terminal task using the Terminal tool (run_command):

Task: {task}

Instructions:
1. First verify current directory and system environment if needed.
2. Formulate and run the required terminal commands step by step.
3. Report command execution output and status cleanly."""

ARGUMENTS = [
    {"name": "task", "description": "Terminal task or command description", "required": True}
]


def get_prompt(task: str = "") -> str:
    return TEMPLATE.format(task=task)
