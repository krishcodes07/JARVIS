"""
Run Command Tool — Production-grade shell command execution with safety, truncation, and background execution.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.core.config import PROJECT_ROOT
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema, truncate_output
from jarvis.tools.sandbox import CommandPolicy, PathSandbox

logger = logging.getLogger(__name__)

# Registry for tracking background tasks started by run_command
_BACKGROUND_TASKS: dict[str, dict[str, Any]] = {}


class RunCommandTool(BaseTool):
    """Execute shell commands with structured output, timeout protection, and background task support."""

    schema = ToolSchema(
        name="run_command",
        description=(
            "Execute a shell command in the workspace and return its structured output (stdout, stderr, exit code, duration). "
            "Supports timeout limits, working directory specification, environment variables, and background execution for long-running processes."
        ),
        category="system",
        aliases=["bash", "sh", "terminal", "exec", "cmd"],
        keywords=["command", "terminal", "shell", "bash", "execute", "run", "cli", "powershell"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="command",
                type="string",
                description="The shell command string to execute.",
                required=True,
            ),
            ToolParameter(
                name="cwd",
                type="string",
                description="Optional working directory path (defaults to current workspace directory).",
                required=False,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Maximum execution time in seconds before terminating (default: 60).",
                required=False,
                default=60,
            ),
            ToolParameter(
                name="is_background",
                type="boolean",
                description="Set to true for long-running background tasks (e.g. dev servers, file watchers). Returns task ID immediately.",
                required=False,
                default=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Run a shell command with industry-standard safety and output management."""
        command = kwargs.get("command", "").strip()
        cwd = kwargs.get("cwd")
        timeout = int(kwargs.get("timeout") or 60)
        is_bg = bool(kwargs.get("is_background") or kwargs.get("background", False))

        if not command:
            return "Error: Command cannot be empty."

        # 1. Command Policy Check (blocks destructive commands)
        policy = self._command_policy()
        try:
            policy.check(command)
        except PermissionError as e:
            return f"Security Policy Violation: {e}"

        # 2. Resolve Working Directory
        resolved_cwd: Path | None = None
        if cwd:
            try:
                resolved_cwd = self.resolve_path(cwd)
                if not resolved_cwd.exists() or not resolved_cwd.is_dir():
                    return f"Error: Working directory does not exist or is not a directory: '{cwd}'"
            except PermissionError as e:
                return f"Permission Error: {e}"
        else:
            resolved_cwd = Path.cwd()

        # 3. Background Task Execution
        if is_bg:
            return await self._execute_background(command, resolved_cwd)

        # 4. Synchronous Execution
        return await self._execute_sync(command, resolved_cwd, timeout)

    async def _execute_sync(self, command: str, cwd: Path, timeout: int) -> str:
        """Execute command synchronously with timeout, tree-killing, and structured output formatting."""
        start_time = time.perf_counter()
        log_file_path: str | None = None

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            # Prepare shell command
            is_win = platform.system() == "Windows"
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except TimeoutError:
                # Terminate process tree cleanly
                self._kill_process_tree(process.pid)
                await process.communicate()
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return (
                    f"Command Timed Out\n"
                    f"Command: `{command}`\n"
                    f"Working Directory: {cwd}\n"
                    f"Duration: {duration_ms}ms\n"
                    f"Error: Execution exceeded {timeout}s timeout limit and was terminated."
                )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            returncode = process.returncode if process.returncode is not None else -1

            stdout_str = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()

            # Save full log if output is large
            combined_len = len(stdout_str) + len(stderr_str)
            if combined_len > 35_000 or stdout_str.count("\n") > 400:
                log_dir = PROJECT_ROOT / "data" / "cache" / "command_logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = log_dir / f"cmd_{timestamp}_{uuid.uuid4().hex[:6]}.log"
                full_log = f"Command: {command}\nCwd: {cwd}\nExit Code: {returncode}\n\nSTDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}"
                log_file.write_text(full_log, encoding="utf-8")
                log_file_path = str(log_file)

            # Apply intelligent head/tail truncation to stdout
            truncated_stdout, _ = truncate_output(
                stdout_str, max_lines=400, max_chars=35_000, log_file_path=log_file_path
            )
            truncated_stderr, _ = truncate_output(
                stderr_str, max_lines=200, max_chars=15_000, log_file_path=log_file_path
            )

            status_str = "SUCCESS" if returncode == 0 else f"FAILED (Exit Code: {returncode})"
            header = (
                f"Command Status: {status_str} | Duration: {duration_ms}ms\n"
                f"Working Directory: {cwd}\n"
                f"{'=' * 60}\n"
            )

            parts = [header]
            if truncated_stdout:
                parts.append(f"STDOUT:\n{truncated_stdout}")
            elif returncode == 0 and not truncated_stderr:
                parts.append("STDOUT: [Command completed with no standard output]")

            if truncated_stderr:
                parts.append(f"\nSTDERR:\n{truncated_stderr}")

            return "\n".join(parts)

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Error executing command '%s': %s", command, e, exc_info=True)
            return (
                f"Command Execution Failed\n"
                f"Command: `{command}`\n"
                f"Working Directory: {cwd}\n"
                f"Duration: {duration_ms}ms\n"
                f"Error: {e}"
            )

    async def _execute_background(self, command: str, cwd: Path) -> str:
        """Launch command asynchronously as a background job."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        log_dir = PROJECT_ROOT / "data" / "cache" / "command_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{task_id}.log"
        log_fp = open(log_file, "w", encoding="utf-8")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(cwd),
                env=env,
            )

            _BACKGROUND_TASKS[task_id] = {
                "task_id": task_id,
                "command": command,
                "cwd": str(cwd),
                "pid": process.pid,
                "process": process,
                "log_file": str(log_file),
                "log_fp": log_fp,
                "started_at": datetime.now().isoformat(),
            }

            return (
                f"Background Task Launched Successfully\n"
                f"Task ID: {task_id}\n"
                f"Process PID: {process.pid}\n"
                f"Command: `{command}`\n"
                f"Working Directory: {cwd}\n"
                f"Log File: {log_file}\n"
                f"Use 'process_manager' to monitor or manage this task."
            )
        except Exception as e:
            log_fp.close()
            return f"Failed to launch background command '{command}': {e}"

    def _kill_process_tree(self, pid: int) -> None:
        """Kill a process and all its child subprocesses across Windows and Unix."""
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                import signal

                killpg = getattr(os, "killpg", None)
                getpgid = getattr(os, "getpgid", None)
                sigkill = getattr(signal, "SIGKILL", getattr(signal, "SIGTERM", 15))
                if killpg and getpgid:
                    killpg(getpgid(pid), sigkill)
                elif hasattr(os, "kill"):
                    os.kill(pid, sigkill)
        except Exception as e:
            logger.debug("Failed to kill process tree for PID %s: %s", pid, e)

    def _command_policy(self) -> CommandPolicy:
        """Build command policy from config."""
        sb = getattr(self, "config", None)
        if sb:
            return CommandPolicy.from_config(sb)
        return CommandPolicy()
