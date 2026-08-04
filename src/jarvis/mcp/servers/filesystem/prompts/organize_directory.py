"""
Prompt workflow for directory organization.
"""

NAME = "Organize Directory"
DESCRIPTION = "Workflow prompt to suggest an optimal folder organizational scheme."
TEMPLATE = """Examine the files in directory '{directory}' and propose a clean directory organization strategy:

- Categorize files by extension or function (e.g., /docs, /data, /scripts).
- List specific file relocation commands.
- Ensure no critical files are deleted."""

ARGUMENTS = [
    {"name": "directory", "description": "Target folder relative path", "required": True}
]


def get_prompt(directory: str = ".") -> str:
    return TEMPLATE.format(directory=directory)
