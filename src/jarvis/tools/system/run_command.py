"""
Run Command Tool — Execute shell commands.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema
from jarvis.tools.sandbox import CommandPolicy, PathSandbox

logger = logging.getLogger(__name__)


class RunCommandTool(BaseTool):
    """Execute shell commands and return output."""

    schema = ToolSchema(
        name="run_command",
        description="Execute a shell command and return its output. Use with caution.",
        category="system",
        parameters=[
            ToolParameter(
                name="command",
                type="string",
                description="The shell command to execute",
            ),
            ToolParameter(
                name="cwd",
                type="string",
                description="Working directory",
                required=False,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Timeout in seconds",
                required=False,
                default=30,
            ),
        ],
        dangerous=True,
    )

    async def execute(self, **kwargs: Any) -> str:
        """Run a shell command."""
        command = kwargs["command"]
        cwd = kwargs.get("cwd")
        timeout = int(kwargs.get("timeout", 30))

        # Command policy check (blocks destructive commands)
        policy = self._command_policy()
        try:
            policy.check(command)
        except PermissionError as e:
            return f"Error: {e}"

        # Resolve working directory against the sandbox
        resolved_cwd = None
        if cwd:
            try:
                resolved_cwd = str(self._resolve_path(cwd))
            except PermissionError as e:
                return f"Error: {e}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=resolved_cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except TimeoutError:
                process.kill()
                await process.communicate()
                return f"Error: Command timed out after {timeout}s and was terminated."

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            result = f"Exit code: {process.returncode}\n"
            if output:
                result += f"Output:\n{output}\n"
            if errors:
                result += f"Stderr:\n{errors}\n"
            return result

        except Exception as e:
            return f"Error executing command: {e}"

    def _command_policy(self) -> CommandPolicy:
        """Build the command policy from config."""
        sb = getattr(self, "config", None)
        if sb:
            return CommandPolicy.from_config(sb)
        return CommandPolicy()

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path against the sandbox, if enabled."""
        sb = getattr(self, "config", None)
        if sb and sb.tools.sandbox.enabled:
            return PathSandbox.from_config(sb).resolve(path)
        return Path(path)
