"""
Run background command tool for Terminal MCP Server.
Launches a long-running subprocess or GUI app silently in the background without opening a terminal window.
"""

import os
import subprocess
import sys
from typing import Optional
from ..config import resolve_cwd

NAME = "run_background_command"
DESCRIPTION = (
    "Launch a long-running command, dev server, or GUI app silently in the background without opening a terminal window "
    "(e.g. npm run dev, python snake.py). Pass the 'cwd' parameter directly to target specific project folders."
)


def run_background_command(
    command: str,
    cwd: Optional[str] = None,
) -> str:
    """
    Launch a command silently in the background without creating a console/terminal window.

    Args:
        command: Command to launch in background (e.g., 'npm run dev', 'python snake.py').
        cwd: Target working directory path (e.g., 'D:/Coding/krish-portfolio'). Default is current directory.

    Returns:
        Process ID and launch confirmation.
    """
    try:
        work_dir = resolve_cwd(cwd)
        if not os.path.exists(work_dir):
            return f"Error: Working directory does not exist: {work_dir}"

        cmd_to_run = command.strip()

        if sys.platform == "win32":
            # Replace python with pythonw for windowless GUI/script execution
            if cmd_to_run.startswith("python "):
                cmd_to_run = "pythonw " + cmd_to_run[7:]
            elif cmd_to_run == "python":
                cmd_to_run = "pythonw"

            # CREATE_NO_WINDOW (0x08000000) prevents Windows from opening any console/terminal window
            CREATE_NO_WINDOW = 0x08000000
            proc = subprocess.Popen(
                cmd_to_run,
                cwd=work_dir,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                cmd_to_run,
                cwd=work_dir,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        return (
            f"[OK] Launched background command silently (no terminal window opened)!\n"
            f"  • PID: {proc.pid}\n"
            f"  • Executed Command: {cmd_to_run}\n"
            f"  • Directory: {work_dir}"
        )

    except Exception as e:
        return f"Error: Failed to launch background command: {e}"
