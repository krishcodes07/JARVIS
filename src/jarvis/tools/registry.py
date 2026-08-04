"""
Tool Registry — Auto-discovers and registers all available tools.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.core.exceptions import ToolNotFoundError
from jarvis.tools.base import BaseTool

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent


class ToolRegistry:
    """Registry of all available JARVIS tools.

    Auto-discovers tools by scanning the tools/ subdirectories
    for classes that subclass BaseTool.

    Usage:
        ```python
        registry = ToolRegistry(config)
        registry.discover_tools()

        tool = registry.get("web_search")
        result = await tool.execute(query="python asyncio")
        ```
    """

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self._tools: dict[str, BaseTool] = {}

    def discover_tools(self) -> None:
        """Auto-discover and register all tools from subdirectories."""
        categories = ["basic", "filesystem", "system", "code"]

        for category in categories:
            # Check if category is enabled
            if not self.config.tools.categories.get(category, True):
                logger.debug(f"Tool category '{category}' is disabled, skipping.")
                continue

            category_dir = TOOLS_DIR / category
            if not category_dir.is_dir():
                continue

            for py_file in category_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"jarvis.tools.{category}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for _name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseTool) and obj is not BaseTool:
                            tool_instance = obj()
                            tool_instance.configure(self.config)
                            self._tools[tool_instance.name] = tool_instance
                            logger.debug(f"Registered tool: {tool_instance.name} ({category})")
                except Exception as e:
                    logger.warning(f"Failed to load tool module {module_name}: {e}")

        logger.info(f"Discovered {len(self._tools)} tools.")

    def register(self, tool: BaseTool) -> None:
        """Manually register a tool.

        Args:
            tool: A BaseTool instance.
        """
        self._tools[tool.name] = tool
        logger.debug(f"Manually registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            The tool instance.

        Raises:
            ToolNotFoundError: If tool is not registered.
        """
        if name not in self._tools:
            available = ", ".join(sorted(self._tools.keys()))
            raise ToolNotFoundError(f"Tool '{name}' not found. Available: {available}")
        return self._tools[name]

    def list_tools(self) -> list[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get JSON schemas for all tools (for LLM function calling)."""
        return [
            {
                "name": tool.schema.name,
                "description": tool.schema.description,
                "parameters": tool.schema.to_json_schema(),
            }
            for tool in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
