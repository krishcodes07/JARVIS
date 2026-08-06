"""
Run command tool for Terminal MCP Server.
Executes shell commands with working directory, timeout, and output capture.
"""

import os
import subprocess
import sys
import time

from ..config import DEFAULT_TIMEOUT, resolve_cwd

NAME = "run_command"
DESCRIPTION = (
    "Execute any terminal command (e.g. npx, npm, git, pip, python, dir, ls, docker) "
    "with working directory (cwd), timeout, and output capture. Always pass the 'cwd' parameter directly "
    "to target specific project folders instead of using 'cd' inside command strings."
)


def run_command(
    command: str,
    cwd: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    shell_type: str = "auto",
) -> str:
    """
    Execute a shell command.

    Args:
        command: The exact command line string to execute (e.g., 'npm run build', 'npx tailwindcss init', 'git status').
        cwd: Target working directory path (e.g., 'D:/Coding/krish-portfolio'). Default is current directory.
        timeout: Maximum execution timeout in seconds (default: 60).
        shell_type: Shell executable to use ('auto', 'cmd', 'powershell', 'bash').

    Returns:
        Command output containing returncode, stdout, stderr, and execution time.
    """
    try:
        work_dir = resolve_cwd(cwd)

        if not os.path.exists(work_dir):
            return f"Error: Working directory does not exist: {work_dir}"

        if sys.platform == "win32":
            if shell_type == "powershell":
                cmd_args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
                use_shell = False
            else:
                cmd_args = command
                use_shell = True
        else:
            if shell_type == "bash":
                cmd_args = ["/bin/bash", "-c", command]
                use_shell = False
            else:
                cmd_args = command
                use_shell = True

        start_time = time.time()

        process = subprocess.Popen(
            cmd_args,
            cwd=work_dir,
            shell=use_shell,
            stdin=subprocess.DEVNULL,  # Prevent commands from hanging indefinitely waiting for stdin input
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        try:
            stdout, stderr = process.communicate(timeout=float(timeout))
            elapsed = time.time() - start_time
            exit_code = process.returncode

            status_symbol = "[OK]" if exit_code == 0 else "[ERROR]"
            output_parts = [
                f"{status_symbol} Terminal Command Executed",
                f"Command: {command}",
                f"Directory: {work_dir}",
                f"Duration: {elapsed:.2f}s | Exit Code: {exit_code}",
                f"{'=' * 60}",
            ]

            if stdout and stdout.strip():
                output_parts.append(f"--- STDOUT ---\n{stdout.strip()}")

            if stderr and stderr.strip():
                output_parts.append(f"--- STDERR ---\n{stderr.strip()}")

            if not stdout.strip() and not stderr.strip():
                output_parts.append("(Command completed with no output)")

            return "\n\n".join(output_parts)

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return (
                f"Error: Command timed out after {timeout} seconds: '{command}'. "
                "Note: For GUI games (Pygame/Tkinter), dev servers, or long-running interactive applications, "
                "use 'run_background_command' instead of 'run_command'."
            )

    except Exception as e:
        return f"Error: Failed to execute command: {e}"
