"""
Unit tests for FileSnapshotManager (file revert functionality across process restarts).
"""

from __future__ import annotations

from pathlib import Path

from jarvis.core.snapshot import FileSnapshotManager


def test_snapshot_edit_revert(tmp_path: Path):
    """Test that editing an existing file is properly reverted to pre-edit contents."""
    manager = FileSnapshotManager()
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Original Content\nLine 2\n")

    sid = "session_1"
    msg_idx = 1
    # 1. Tool call triggers pre-edit backup
    manager.backup_tool_call(sid, msg_idx, "edit_file", {"path": str(file_path)})

    # 2. Tool modifies file
    file_path.write_text("Modified Content\nLine 2 Added\nLine 3\n")
    assert "Modified" in file_path.read_text()

    # 3. User reverts turn 1
    restored = manager.restore_checkpoint(sid, msg_idx)
    assert restored is True
    assert file_path.read_text() == "Original Content\nLine 2\n"


def test_snapshot_creation_revert(tmp_path: Path):
    """Test that creating a new file is properly deleted on revert."""
    manager = FileSnapshotManager()
    file_path = tmp_path / "new_file.txt"

    sid = "session_2"
    msg_idx = 1
    # 1. Tool call triggers pre-creation backup (file does not exist)
    manager.backup_tool_call(sid, msg_idx, "write_file", {"path": str(file_path)})

    # 2. Tool writes new file
    file_path.write_text("Brand new file content")
    assert file_path.exists()

    # 3. User reverts turn 1
    restored = manager.restore_checkpoint(sid, msg_idx)
    assert restored is True
    assert not file_path.exists()


def test_snapshot_persistence_across_restarts(tmp_path: Path):
    """Test that snapshots saved by one manager instance can be restored by a fresh instance after app restart."""
    file_path = tmp_path / "restart_test.txt"
    file_path.write_text("Before Restart State")

    sid = "session_restart_test"
    msg_idx = 1

    # Instance A (first run): backs up file and makes edits
    manager1 = FileSnapshotManager()
    manager1.backup_tool_call(sid, msg_idx, "edit_file", {"path": str(file_path)})
    file_path.write_text("After JARVIS Edit - State Changed")

    # Instance B (simulates restarting JARVIS application):
    manager2 = FileSnapshotManager()
    # Reverting from the fresh instance should read snapshots from disk and restore the file!
    restored = manager2.restore_checkpoint(sid, msg_idx)
    assert restored is True
    assert file_path.read_text() == "Before Restart State"
