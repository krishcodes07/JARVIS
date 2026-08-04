"""
Prompt workflow for analyzing a codebase directory.
"""

NAME = "Analyze Codebase"
DESCRIPTION = "Workflow prompt to analyze structure, dependencies, and code quality of a directory."
TEMPLATE = """Please review the codebase in folder '{path}' (resource: filesystem://allowed_directory) and perform a comprehensive review:

1. **Architecture & Structure**: Group components logically and identify entry points.
2. **Code Quality & Patterns**: Note any anti-patterns, duplicated logic, or missing type hints.
3. **Recommendations**: Highlight top 3 improvements for scalability and maintainability."""

ARGUMENTS = [
    {"name": "path", "description": "Subdirectory to analyze (default: '.')", "required": False}
]


def get_prompt(path: str = ".") -> str:
    """Generate the formatted codebase analysis prompt."""
    return TEMPLATE.format(path=path)
