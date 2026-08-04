"""
Example Resource template file.
Every resource file in resources/ is automatically discovered and loaded.
"""

URI = "my_server://example_resource"
NAME = "Example Resource"
DESCRIPTION = "An example contextual resource demonstrating dynamic discovery."
MIME_TYPE = "text/plain"


def example_resource() -> str:
    """Read-only loader function returning contextual information."""
    return "This is the content of example_resource from my_server."
