"""
Example Prompt template file.
Every prompt file in prompts/ is automatically discovered and loaded.
"""

NAME = "Example Workflow Prompt"
DESCRIPTION = "An example workflow prompt template."
TEMPLATE = """Perform an example workflow for subject '{subject}':

1. Review contextual info for '{subject}'.
2. Generate summary report."""

ARGUMENTS = [
    {"name": "subject", "description": "Subject of the workflow", "required": True}
]


def get_prompt(subject: str = "Demo") -> str:
    """Returns the formatted prompt template."""
    return TEMPLATE.format(subject=subject)
