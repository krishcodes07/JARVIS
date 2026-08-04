"""
Example Tool template file.
Every tool file in tools/ is automatically discovered and loaded.
"""

NAME = "example_tool"
DESCRIPTION = "An example tool function demonstrating automatic dynamic discovery."


def example_tool(param1: str, param2: int = 10) -> str:
    """
    Example tool operation.

    Args:
        param1: First parameter description.
        param2: Second parameter description (default: 10).

    Returns:
        String result message.
    """
    try:
        return f"✅ Executed example_tool with param1='{param1}' and param2={param2}"
    except Exception as e:
        return f"❌ Error executing tool: {e}"
