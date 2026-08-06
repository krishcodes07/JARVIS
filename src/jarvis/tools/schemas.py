"""
Tool Schemas — Shared schema utilities for tool definitions.
"""

from __future__ import annotations

from jarvis.tools.base import ToolParameter


def string_param(name: str, description: str, required: bool = True) -> ToolParameter:
    """Create a string parameter."""
    return ToolParameter(name=name, type="string", description=description, required=required)


def int_param(name: str, description: str, required: bool = True) -> ToolParameter:
    """Create an integer parameter."""
    return ToolParameter(name=name, type="integer", description=description, required=required)


def bool_param(name: str, description: str, required: bool = False) -> ToolParameter:
    """Create a boolean parameter."""
    return ToolParameter(name=name, type="boolean", description=description, required=required)


def enum_param(
    name: str, description: str, options: list[str], required: bool = True
) -> ToolParameter:
    """Create an enum parameter."""
    return ToolParameter(
        name=name, type="string", description=description, required=required, enum=options
    )
