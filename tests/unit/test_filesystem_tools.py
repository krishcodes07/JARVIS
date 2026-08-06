"""
Unit tests for native filesystem tools in jarvis.tools.filesystem.
"""

import pytest

from jarvis.core.config import JarvisConfig
from jarvis.tools.filesystem.delete_file import DeleteFileTool
from jarvis.tools.filesystem.edit_file import EditFileTool
from jarvis.tools.filesystem.grep_search import GrepSearchTool
from jarvis.tools.filesystem.list_directory import ListDirectoryTool
from jarvis.tools.filesystem.read_file import ReadFileTool
from jarvis.tools.filesystem.write_file import WriteFileTool
from jarvis.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_filesystem_tools_discovery():
    config = JarvisConfig.load()
    registry = ToolRegistry(config)
    registry.discover_tools()

    fs_tools = ["read_file", "write_file", "append_file", "edit_file", "list_directory",
                "make_directory", "delete_file", "copy_file", "move_file", "get_file_info",
                "search_files", "grep_search"]

    for name in fs_tools:
        assert name in registry, f"Tool '{name}' not found in registry"
        tool = registry.get(name)
        assert tool.category == "filesystem"


@pytest.mark.asyncio
async def test_filesystem_tools_execution(tmp_path):
    test_file = tmp_path / "sample.txt"
    test_path = str(test_file)

    # 1. Write file
    writer = WriteFileTool()
    write_res = await writer.execute(path=test_path, content="Line 1: Hello JARVIS\nLine 2: Python Testing\nLine 3: End")
    assert "Wrote" in write_res
    assert test_file.exists()

    # 2. Read file
    reader = ReadFileTool()
    read_res = await reader.execute(path=test_path, start_line=1, end_line=2)
    assert "Hello JARVIS" in read_res
    assert "Python Testing" in read_res

    # 3. Edit file
    editor = EditFileTool()
    edit_res = await editor.execute(path=test_path, find_text="Python Testing", replace_text="Advanced Tools")
    assert "Replaced 1 occurrence(s)" in edit_res

    # 4. List directory
    lister = ListDirectoryTool()
    list_res = await lister.execute(path=str(tmp_path))
    assert "sample.txt" in list_res

    # 5. Grep search
    grepper = GrepSearchTool()
    grep_res = await grepper.execute(path=str(tmp_path), query="Advanced Tools")
    assert "Advanced Tools" in grep_res

    # 6. Delete file
    deleter = DeleteFileTool()
    del_res = await deleter.execute(path=test_path)
    assert "Successfully deleted file" in del_res
    assert not test_file.exists()
