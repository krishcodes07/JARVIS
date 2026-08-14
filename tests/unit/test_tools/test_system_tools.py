"""
Unit tests for system tools: run_command, process_manager, and system_info.
"""

import os
import sys
import pytest

from jarvis.core.config import JarvisConfig
from jarvis.tools.system.process_manager import ProcessManagerTool
from jarvis.tools.system.run_command import RunCommandTool
from jarvis.tools.system.system_info import SystemInfoTool


@pytest.mark.asyncio
async def test_run_command_sync():
    tool = RunCommandTool()
    cmd = f'"{sys.executable}" -c "print(\'JARVIS System Test\')"'
    res = await tool.execute(command=cmd)
    assert "SUCCESS" in res
    assert "JARVIS System Test" in res
    assert "Duration:" in res


@pytest.mark.asyncio
async def test_run_command_exit_code_failure():
    tool = RunCommandTool()
    cmd = f'"{sys.executable}" -c "import sys; sys.exit(42)"'
    res = await tool.execute(command=cmd)
    assert "Exit Code: 42" in res


@pytest.mark.asyncio
async def test_run_command_security_policy():
    tool = RunCommandTool()
    res = await tool.execute(command="rm -rf /")
    assert "Violation" in res or "blocked" in res.lower()


@pytest.mark.asyncio
async def test_run_command_background_task():
    tool = RunCommandTool()
    cmd = f'"{sys.executable}" -c "import time; time.sleep(1)"'
    res = await tool.execute(command=cmd, is_background=True)
    assert "Background Task Launched" in res
    assert "Task ID:" in res


@pytest.mark.asyncio
async def test_process_manager_list():
    tool = ProcessManagerTool()
    res = await tool.execute(action="list")
    assert "System Processes" in res or "PID" in res


@pytest.mark.asyncio
async def test_process_manager_self_kill_safety():
    tool = ProcessManagerTool()
    res = await tool.execute(action="kill", pid=os.getpid())
    assert "Permission Denied" in res or "Refusing" in res


@pytest.mark.asyncio
async def test_process_manager_info():
    tool = ProcessManagerTool()
    res = await tool.execute(action="info", pid=os.getpid())
    assert "Process Information" in res


@pytest.mark.asyncio
async def test_system_info():
    tool = SystemInfoTool()
    res = await tool.execute()
    assert "Operating System" in res
    assert "Python Environment" in res
    assert "Architecture" in res
