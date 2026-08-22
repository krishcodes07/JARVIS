"""
Process Manager Tool — List, inspect, and terminate system processes and background tasks.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema
from jarvis.tools.system.run_command import _BACKGROUND_TASKS

logger = logging.getLogger(__name__)


@dataclass
class ProcessEntry:
    pid: int
    name: str
    mem_mb: float
    cpu: float
    status: str


class ProcessManagerTool(BaseTool):
    """List running processes, check resource usage, or terminate processes and background jobs."""

    schema = ToolSchema(
        name="process_manager",
        description=(
            "Manage system processes and background tasks. "
            "Actions: 'list' (shows active background tasks and top system processes), "
            "'kill' (terminates a process by PID or background task_id), "
            "'info' (gets detailed resource usage and status for a PID or task_id)."
        ),
        category="system",
        aliases=["ps", "kill_process", "task_manager"],
        keywords=["process", "tasks", "kill", "ps", "pid", "memory", "cpu", "terminate"],
        dangerous=True,
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'list', 'kill', or 'info'.",
                required=True,
                enum=["list", "kill", "info"],
            ),
            ToolParameter(
                name="pid",
                type="integer",
                description="Process ID (PID) to inspect or terminate.",
                required=False,
            ),
            ToolParameter(
                name="task_id",
                type="string",
                description="Background Task ID (e.g. 'task_1a2b3c4d') to inspect or terminate.",
                required=False,
            ),
            ToolParameter(
                name="name",
                type="string",
                description="Optional process name filter (for 'list' action).",
                required=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute process management action."""
        action = kwargs.get("action", "list").lower().strip()
        pid = kwargs.get("pid")
        task_id = kwargs.get("task_id")
        name_filter = kwargs.get("name")

        if action == "list":
            return self._list_processes(name_filter)
        elif action == "kill":
            return self._kill_process(pid=pid, task_id=task_id)
        elif action == "info":
            return self._get_process_info(pid=pid, task_id=task_id)
        else:
            return f"Error: Unknown action '{action}'. Valid actions are 'list', 'kill', 'info'."

    def _list_processes(self, name_filter: str | None = None) -> str:
        """List active background tasks and top system processes."""
        output_parts: list[str] = []

        # 1. List JARVIS background tasks
        if _BACKGROUND_TASKS:
            output_parts.append("### Active JARVIS Background Tasks:")
            for tid, tinfo in list(_BACKGROUND_TASKS.items()):
                proc = tinfo.get("process")
                is_running = proc is not None and proc.returncode is None
                status = "RUNNING" if is_running else f"FINISHED (Code: {proc.returncode if proc else 'N/A'})"
                output_parts.append(
                    f"  • Task ID: `{tid}` | PID: {tinfo.get('pid')} | Status: {status}\n"
                    f"    Command: `{tinfo.get('command')}` | Log: {tinfo.get('log_file')}"
                )
            output_parts.append("\n" + "=" * 60 + "\n")

        # 2. List system processes (using psutil or OS native commands)
        try:
            import psutil  # type: ignore

            output_parts.append("### System Processes (Top by Memory/CPU):")
            output_parts.append(f"{'PID':<8} {'Name':<25} {'Memory (MB)':<14} {'CPU %':<8} {'Status':<10}")
            output_parts.append("-" * 65)

            procs: list[ProcessEntry] = []
            for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "status"]):
                try:
                    pinfo = p.info
                    p_name = str(pinfo.get("name") or "unknown")
                    if name_filter and name_filter.lower() not in p_name.lower():
                        continue
                    mem_mb = (pinfo["memory_info"].rss / (1024 * 1024)) if pinfo.get("memory_info") else 0.0
                    cpu_pct = float(pinfo.get("cpu_percent") or 0.0)
                    status_str = str(pinfo.get("status") or "active")
                    procs.append(ProcessEntry(
                        pid=int(pinfo.get("pid") or 0),
                        name=p_name,
                        mem_mb=float(mem_mb),
                        cpu=cpu_pct,
                        status=status_str,
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by memory usage descending
            procs.sort(key=lambda x: x.mem_mb, reverse=True)
            for pe in procs[:25]:
                output_parts.append(
                    f"{pe.pid:<8} {pe.name[:24]:<25} {pe.mem_mb:>10.1f} MB   {pe.cpu:>5.1f}%  {pe.status:<10}"
                )

            return "\n".join(output_parts)

        except ImportError:
            # Fallback to native OS tools
            return self._list_processes_native_fallback(name_filter, output_parts)

    def _list_processes_native_fallback(self, name_filter: str | None, base_parts: list[str]) -> str:
        """Fallback process listing using OS built-in commands."""
        base_parts.append("### System Processes:")
        try:
            if platform.system() == "Windows":
                cmd = ["tasklist", "/FO", "TABLE", "/NH"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                lines = res.stdout.strip().splitlines()
                base_parts.append(f"{'Image Name':<30} {'PID':<10} {'Mem Usage':<15}")
                base_parts.append("-" * 55)
                count = 0
                for line in lines:
                    if name_filter and name_filter.lower() not in line.lower():
                        continue
                    parts = line.split()
                    if len(parts) >= 5:
                        p_name = parts[0]
                        p_pid = parts[1]
                        p_mem = " ".join(parts[-2:])
                        base_parts.append(f"{p_name[:28]:<30} {p_pid:<10} {p_mem:<15}")
                        count += 1
                        if count >= 30:
                            break
            else:
                cmd = ["ps", "aux"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                lines = res.stdout.strip().splitlines()
                base_parts.extend(lines[:30])

            return "\n".join(base_parts)
        except Exception as e:
            base_parts.append(f"Error listing processes via OS command: {e}")
            return "\n".join(base_parts)

    def _kill_process(self, pid: int | None, task_id: str | None) -> str:
        """Terminate a process or background task safely."""
        target_pid = pid

        # Check background tasks first if task_id provided
        if task_id:
            task_info = _BACKGROUND_TASKS.get(task_id)
            if not task_info:
                return f"Error: Background task '{task_id}' not found."
            target_pid = task_info.get("pid")
            proc = task_info.get("process")
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            log_fp = task_info.get("log_fp")
            if log_fp and not log_fp.closed:
                log_fp.close()

        if target_pid is None:
            return "Error: Please specify either 'pid' or 'task_id' to terminate."

        # Safety checks for critical system PIDs
        if target_pid in (0, 4, 1):
            return f"Permission Denied: Refusing to terminate critical system process PID {target_pid}."
        if target_pid == os.getpid():
            return f"Permission Denied: Refusing to terminate JARVIS self process PID {target_pid}."

        try:
            import psutil  # type: ignore

            proc = psutil.Process(target_pid)
            proc_name = proc.name()
            # Terminate children
            for child in proc.children(recursive=True):
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            proc.kill()
            return f"Successfully terminated process '{proc_name}' (PID: {target_pid})."

        except ImportError:
            # Native OS kill
            try:
                if platform.system() == "Windows":
                    res = subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(target_pid)],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if res.returncode == 0:
                        return f"Successfully terminated process PID {target_pid}."
                    return f"Failed to terminate PID {target_pid}: {res.stderr.strip()}"
                else:
                    import signal

                    sigkill = getattr(signal, "SIGKILL", getattr(signal, "SIGTERM", 15))
                    os.kill(target_pid, sigkill)
                    return f"Successfully terminated process PID {target_pid}."
            except Exception as e:
                return f"Error terminating PID {target_pid}: {e}"
        except Exception as e:
            return f"Error terminating PID {target_pid}: {e}"

    def _get_process_info(self, pid: int | None, task_id: str | None) -> str:
        """Get detailed telemetry for a PID or task_id."""
        target_pid = pid
        task_info = None

        if task_id:
            task_info = _BACKGROUND_TASKS.get(task_id)
            if task_info:
                target_pid = task_info.get("pid")

        if target_pid is None:
            return "Error: Please specify either 'pid' or 'task_id' to get info."

        lines = [f"Process Information (PID: {target_pid}):"]
        if task_info:
            lines.append(f"  • Task ID: {task_id}")
            lines.append(f"  • Command: {task_info.get('command')}")
            lines.append(f"  • Started At: {task_info.get('started_at')}")
            lines.append(f"  • Log File: {task_info.get('log_file')}")

        try:
            import psutil  # type: ignore

            p = psutil.Process(target_pid)
            with p.oneshot():
                lines.append(f"  • Name: {p.name()}")
                lines.append(f"  • Status: {p.status()}")
                lines.append(f"  • CPU Percent: {p.cpu_percent(interval=0.1):.1f}%")
                lines.append(f"  • Memory (RSS): {p.memory_info().rss / (1024 * 1024):.1f} MB")
                lines.append(f"  • Executable: {p.exe()}")
                lines.append(f"  • Working Dir: {p.cwd()}")
                lines.append(f"  • Command Line: {' '.join(p.cmdline())}")
                lines.append(f"  • Threads: {p.num_threads()}")

            return "\n".join(lines)
        except Exception as e:
            lines.append(f"  • Note: Could not retrieve extended psutil details ({e}).")
            return "\n".join(lines)
