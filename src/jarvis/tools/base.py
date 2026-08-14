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

import difflib
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def is_binary_file(path: str | Path, sample_size: int = 8192) -> bool:
    """Check whether a file is binary by inspecting its initial byte sample for null bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
            if not chunk:
                return False
            # Check for null bytes or excessive non-text control characters
            if b"\x00" in chunk:
                return True
            # Check non-printable characters ratio
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
            non_text = chunk.translate(None, text_chars)
            return len(non_text) / len(chunk) > 0.30
    except Exception:
        return False


def format_unified_diff(
    original_text: str,
    modified_text: str,
    from_file: str = "original",
    to_file: str = "modified",
) -> str:
    """Generate a clean unified diff string between original and modified text."""
    orig_lines = original_text.splitlines(keepends=True)
    mod_lines = modified_text.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=from_file,
            tofile=to_file,
            lineterm="",
        )
    )
    if not diff:
        return "[No changes detected]"
    return "\n".join(diff)


def atomic_write_text(
    filepath: Path,
    content: str,
    encoding: str = "utf-8",
) -> None:
    """Write text content to a file atomically using a temporary file in the same directory."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Create temp file in same directory to ensure same filesystem for atomic os.replace
    dir_path = str(filepath.parent)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=dir_path,
        delete=False,
        suffix=".tmp",
    ) as tf:
        temp_name = tf.name
        tf.write(content)
        tf.flush()
        os.fsync(tf.fileno())

    os.replace(temp_name, filepath)


def truncate_output(
    text: str,
    max_lines: int = 400,
    max_chars: int = 35_000,
    head_lines: int = 100,
    tail_lines: int = 100,
    log_file_path: str | None = None,
) -> tuple[str, bool]:
    """Intelligently truncate output preserving head and tail lines if limits are exceeded.

    Returns:
        tuple[str, bool]: (truncated_or_original_text, was_truncated)
    """
    lines = text.splitlines(keepends=True)
    total_lines = len(lines)
    total_chars = len(text)

    if total_lines <= max_lines and total_chars <= max_chars:
        return text, False

    # Extract head and tail
    head = lines[:head_lines]
    tail = lines[-tail_lines:] if total_lines > head_lines + tail_lines else []

    omitted_lines = max(0, total_lines - len(head) - len(tail))
    omitted_chars = max(0, total_chars - sum(len(l) for l in head) - sum(len(l) for l in tail))

    log_notice = f" Full output saved to: {log_file_path}" if log_file_path else ""
    truncation_banner = (
        f"\n\n[... Output truncated: {omitted_lines:,} lines ({omitted_chars:,} chars) skipped.{log_notice} ...]\n\n"
    )

    truncated_text = "".join(head) + truncation_banner + "".join(tail)
    return truncated_text, True


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
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
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
    """Abstract base class for all JARVIS tools."""

    schema: ToolSchema

    def configure(self, config: Any) -> None:
        """Called once after instantiation with the loaded JarvisConfig."""
        self.config: Any = config

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path against the sandbox if enabled, or return absolute path."""
        from jarvis.tools.sandbox import PathSandbox

        cfg = getattr(self, "config", None)
        if cfg and hasattr(cfg, "tools") and cfg.tools and hasattr(cfg.tools, "sandbox") and cfg.tools.sandbox.enabled:
            return PathSandbox.from_config(cfg).resolve(path)

        return Path(path).expanduser().resolve()

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments."""
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

