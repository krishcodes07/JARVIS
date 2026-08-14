"""
System Info Tool — Comprehensive telemetry and diagnostics for system hardware and environment.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from typing import Any

from jarvis.tools.base import BaseTool, ToolSchema

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    """Retrieve comprehensive system telemetry: OS, CPU, RAM, disk, Python environment, and GPU."""

    schema = ToolSchema(
        name="system_info",
        description="Get rich system information: OS, CPU cores & usage, Memory (RAM), Disk storage, Python environment, and GPU availability.",
        category="system",
        aliases=["sysinfo", "specs", "host_info"],
        keywords=["system", "info", "cpu", "memory", "ram", "disk", "os", "specs", "hardware", "gpu"],
        parameters=[],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Collect and format system diagnostics."""
        lines = ["System Information & Hardware Telemetry:"]
        lines.append("=" * 55)

        # 1. Operating System
        lines.append("### Operating System:")
        lines.append(f"  • OS: {platform.system()} {platform.release()} (Build {platform.version()})")
        lines.append(f"  • Architecture: {platform.machine()} ({platform.architecture()[0]})")
        lines.append(f"  • Hostname: {platform.node()}")
        lines.append(f"  • Current User: {os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USERNAME', 'N/A')}")

        # 2. CPU & Memory
        lines.append("\n### Processor & Memory:")
        try:
            import psutil  # type: ignore

            cpu_count_phys = psutil.cpu_count(logical=False) or "N/A"
            cpu_count_log = psutil.cpu_count(logical=True) or os.cpu_count() or "N/A"
            cpu_usage = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            lines.append(f"  • CPU: {platform.processor() or platform.machine()}")
            lines.append(f"  • Cores: {cpu_count_phys} physical / {cpu_count_log} logical threads")
            lines.append(f"  • CPU Utilization: {cpu_usage:.1f}%")
            lines.append(
                f"  • RAM: {mem.used / (1024**3):.2f} GB used / {mem.total / (1024**3):.2f} GB total "
                f"({mem.percent}% used, {mem.available / (1024**3):.2f} GB available)"
            )
        except ImportError:
            cores = os.cpu_count() or "N/A"
            lines.append(f"  • CPU: {platform.processor() or platform.machine()} ({cores} cores)")
            lines.append("  • RAM: (Install psutil for detailed RAM metrics)")

        # 3. Disk Storage (Current Workspace Drive)
        lines.append("\n### Storage (Workspace Volume):")
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            pct_used = (used / total) * 100 if total > 0 else 0.0
            lines.append(
                f"  • Workspace Disk: {used / (1024**3):.1f} GB used / {total / (1024**3):.1f} GB total "
                f"({pct_used:.1f}% used, {free / (1024**3):.1f} GB free)"
            )
        except Exception as e:
            lines.append(f"  • Disk: Could not query disk usage ({e})")

        # 4. Python Environment
        lines.append("\n### Python Environment:")
        in_venv = sys.prefix != sys.base_prefix
        lines.append(f"  • Python Version: {platform.python_version()} ({platform.python_implementation()})")
        lines.append(f"  • Executable: {sys.executable}")
        lines.append(f"  • Virtual Environment: {'Active (' + sys.prefix + ')' if in_venv else 'Inactive (System Python)'}")
        lines.append(f"  • Working Directory: {os.getcwd()}")

        # 5. GPU Telemetry
        gpu_info = self._get_gpu_info()
        if gpu_info:
            lines.append("\n### GPU Acceleration:")
            lines.append(f"  • {gpu_info}")

        return "\n".join(lines)

    def _get_gpu_info(self) -> str | None:
        """Check for NVIDIA GPU via nvidia-smi."""
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                gpu_lines = res.stdout.strip().splitlines()
                details = []
                for idx, line in enumerate(gpu_lines):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        name, total_mb, used_mb, util = parts[0], parts[1], parts[2], parts[3]
                        details.append(f"GPU {idx} ({name}): {used_mb}MB / {total_mb}MB ({util}% load)")
                return "; ".join(details)
        except Exception:
            pass
        return None
