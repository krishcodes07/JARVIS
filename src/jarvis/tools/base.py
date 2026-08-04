"""
Base Tool — Abstract interface and decorators for tool definitions.

Every tool must subclass BaseTool and implement the execute() method.
Tools are auto-discovered by the ToolRegistry.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """A single tool parameter definition."""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


class ToolSchema(BaseModel):
    """Complete tool schema for LLM function calling."""
    name: str
    description: str
    category: str = "basic"
    parameters: list[ToolParameter] = Field(default_factory=list)
    dangerous: bool = False  # Requires user confirmation if auto_approve is False

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format (for OpenAI function calling)."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema


class BaseTool(ABC):
    """Abstract base class for all JARVIS tools.

    Subclass this and implement:
    - schema: Define the tool's name, description, and parameters
    - execute(): Implement the tool's logic

    Example:
        ```python
        class WebSearchTool(BaseTool):
            schema = ToolSchema(
                name="web_search",
                description="Search the web",
                parameters=[
                    ToolParameter(name="query", type="string", description="Search query"),
                ],
            )

            async def execute(self, **kwargs) -> str:
                query = kwargs["query"]
                # ... perform search ...
                return results
        ```
    """

    schema: ToolSchema

    def configure(self, config: Any) -> None:
        """Called once after instantiation with the loaded JarvisConfig.

        Tools that need access to configuration (e.g. sandbox settings)
        should override this to store the config.
        """
        self.config: Any = config

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments.

        Args:
            **kwargs: Tool-specific arguments matching the schema parameters.

        Returns:
            String result to send back to the LLM.
        """
        ...

    @property
    def name(self) -> str:
        """Tool name."""
        return self.schema.name

    @property
    def description(self) -> str:
        """Tool description."""
        return self.schema.description

    @property
    def category(self) -> str:
        """Tool category."""
        return self.schema.category

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
