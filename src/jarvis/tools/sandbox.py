"""
Tool Sandbox — Path validation and command policy for safe tool execution.

Provides two layers of protection for dangerous tools:
- PathSandbox: Restricts filesystem access to allowed roots.
- CommandPolicy: Blocks known-destructive shell commands.

Both are configurable via the ``tools.sandbox`` section of jarvis.yaml.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Commands that are never allowed regardless of approval.
DEFAULT_BLOCKED_COMMAND_PATTERNS: list[str] = [
    r"(^|[;&|]\s*)rm\s+-rf\s+/",          # Linux: recursive delete of root
    r"(^|[;&|]\s*)rm\s+-rf\s*~",           # Linux: recursive delete of home
    r"(^|[;&|]\s*)format\s+[a-zA-Z]:",     # Windows: format drive
    r"(^|[;&|]\s*)rd\s+/s\s+/q\s+[a-zA-Z]:",  # Windows: recursive delete of drive root
    r"(^|[;&|]\s*)del\s+/s\s+/q\s+[a-zA-Z]:",  # Windows: recursive delete of drive root
    r"(^|[;&|]\s*)diskpart",               # Windows: disk partitioning
    r"(^|[;&|]\s*)shutdown",               # System shutdown / restart
    r"(^|[;&|]\s*)mkfs",                   # Linux: format filesystem
    r"(^|[;&|]\s*)dd\s+if=.*of=\s*/dev/",  # Linux: raw device writes
]


class PathSandbox:
    """Validates that file paths stay within an allowed set of roots.

    All path checks resolve symlinks and relative segments before comparing,
    so ``..`` tricks and symlink escapes are rejected.
    """

    def __init__(
        self,
        workspace: str | Path = ".",
        extra_paths: list[str] | None = None,
    ) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self._allowed = [self.workspace]
        for path in extra_paths or []:
            resolved = Path(path).expanduser().resolve()
            self._allowed.append(resolved)

    @classmethod
    def from_config(cls, config: Any) -> PathSandbox:
        """Build a PathSandbox from the ``tools.sandbox`` config section."""
        sb = config.tools.sandbox
        return cls(workspace=sb.workspace, extra_paths=sb.extra_paths)

    @property
    def allowed_roots(self) -> list[Path]:
        """The list of allowed path roots."""
        return list(self._allowed)

    def resolve(self, path: str | Path) -> Path:
        """Resolve a path and enforce that it stays inside the sandbox.

        Args:
            path: The path to validate.

        Returns:
            The fully resolved absolute path.

        Raises:
            PermissionError: If the resolved path escapes the sandbox.
        """
        if path == "" or path is None:
            raise PermissionError("Empty path is not allowed.")

        candidate = Path(str(path)).expanduser().resolve()

        for base in self._allowed:
            try:
                candidate.relative_to(base)
                return candidate
            except ValueError:
                continue

        roots = ", ".join(str(p) for p in self._allowed)
        raise PermissionError(
            f"Path '{candidate}' is outside the allowed sandbox. "
            f"Allowed roots: [{roots}]. Use tools.sandbox.extra_paths to add more."
        )

    def is_allowed(self, path: str | Path) -> bool:
        """Return True if the path is allowed, without raising."""
        try:
            self.resolve(path)
            return True
        except PermissionError:
            return False


class CommandPolicy:
    """Blocks known-destructive shell commands.

    The policy is a second line of defense on top of the approval gate:
    even an approved ``run_command`` call cannot run commands matching the
    blocked patterns.
    """

    def __init__(self, extra_blocked: list[str] | None = None) -> None:
        patterns = DEFAULT_BLOCKED_COMMAND_PATTERNS + list(extra_blocked or [])
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    @classmethod
    def from_config(cls, config: Any) -> CommandPolicy:
        """Build a CommandPolicy from the ``tools.sandbox`` config section."""
        return cls(extra_blocked=config.tools.sandbox.blocked_commands)

    def is_blocked(self, command: str) -> bool:
        """Return True if the command matches a blocked pattern."""
        return any(pattern.search(command) for pattern in self._patterns)

    def check(self, command: str) -> None:
        """Raise PermissionError if the command is blocked."""
        if self.is_blocked(command):
            raise PermissionError(
                f"Command '{command}' is blocked by the command policy. "
                "It is considered destructive or unsafe."
            )
