"""
File Snapshot Manager — Tracks and restores file state changes per conversation message index.

Persists file snapshots to disk (~/.jarvis/workspace/snapshots/<session_id>/<msg_index>/)
so that reverting message changes works reliably across JARVIS restarts.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from jarvis.core.paths import get_snapshots_dir

logger = logging.getLogger(__name__)


class FileSnapshotManager:
    """Manages exact file snapshots per session and message index for bulletproof revert functionality."""

    def _get_msg_dir(self, session_id: str, msg_index: int) -> Path:
        """Get snapshot directory for a given session and message index."""
        d = get_snapshots_dir() / session_id / str(msg_index)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def start_checkpoint(self, session_id: str, msg_index: int) -> None:
        """Initialize a snapshot directory for a given session and message index."""
        self._get_msg_dir(session_id, msg_index)

    def backup_path(self, session_id: str, msg_index: int, path: str | Path) -> None:
        """Back up the initial state of a file path before modification."""
        if not path or not session_id:
            return

        try:
            abs_p = Path(path).expanduser().resolve()
            msg_dir = self._get_msg_dir(session_id, msg_index)
            meta_file = msg_dir / "meta.json"

            meta: dict[str, Any] = {"paths": {}}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    meta = {"paths": {}}

            path_key = str(abs_p)

            # Preserve only the initial pre-modification state for this message turn
            if path_key in meta.get("paths", {}):
                return

            paths_meta = meta.setdefault("paths", {})

            if abs_p.exists() and abs_p.is_file():
                try:
                    backup_filename = f"snap_{len(paths_meta)}.bin"
                    backup_path = msg_dir / backup_filename
                    backup_path.write_bytes(abs_p.read_bytes())

                    paths_meta[path_key] = {
                        "exists": True,
                        "file": backup_filename,
                    }
                    logger.debug(f"Backed up file state for '{abs_p}' in session {session_id} at msg {msg_index}")
                except Exception as e:
                    logger.warning(f"Could not read file for backup '{abs_p}': {e}")
            elif not abs_p.exists():
                paths_meta[path_key] = {
                    "exists": False,
                    "file": None,
                }
                logger.debug(f"Marked non-existent file path '{abs_p}' in session {session_id} at msg {msg_index}")

            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Error backing up path '{path}' in session {session_id}: {e}")

    def backup_tool_call(
        self,
        session_id: str,
        msg_index: int,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> None:
        """Inspect tool arguments and back up all relevant files before tool execution."""
        paths_to_backup: list[str] = []

        # Common file path keys used across filesystem tools
        keys = (
            "path",
            "file",
            "filepath",
            "target_file",
            "source",
            "destination",
            "src",
            "dst",
            "target",
        )

        for k in keys:
            val = tool_args.get(k)
            if isinstance(val, str) and val.strip():
                paths_to_backup.append(val.strip())
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.strip():
                        paths_to_backup.append(item.strip())

        for p in set(paths_to_backup):
            self.backup_path(session_id, msg_index, p)

    def restore_checkpoint(self, session_id: str, msg_index: int) -> bool:
        """Restore all files modified in checkpoints from msg_index onward."""
        if not session_id:
            return False

        session_dir = get_snapshots_dir() / session_id
        if not session_dir.exists():
            return False

        # Find all message index subdirectories >= msg_index
        k_dirs: list[tuple[int, Path]] = []
        for child in session_dir.iterdir():
            if child.is_dir() and child.name.isdigit():
                idx = int(child.name)
                if idx >= msg_index:
                    k_dirs.append((idx, child))

        if not k_dirs:
            return False

        # Sort descending by message index so latest changes are reverted first
        k_dirs.sort(key=lambda x: x[0], reverse=True)

        restored_any = False
        for _, k_dir in k_dirs:
            meta_file = k_dir / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    paths_meta = meta.get("paths", {})

                    for path_str, info in paths_meta.items():
                        try:
                            abs_p = Path(path_str)
                            exists_before = info.get("exists", False)
                            backup_file_name = info.get("file")

                            if not exists_before:
                                # File was created during or after msg_index -> delete if present
                                if abs_p.exists() and abs_p.is_file():
                                    abs_p.unlink()
                                    restored_any = True
                                    logger.info(f"Revert: Deleted created file '{abs_p}'")
                            else:
                                # File was modified/deleted -> restore original content
                                if backup_file_name:
                                    backup_file = k_dir / backup_file_name
                                    if backup_file.exists():
                                        abs_p.parent.mkdir(parents=True, exist_ok=True)
                                        abs_p.write_bytes(backup_file.read_bytes())
                                        restored_any = True
                                        logger.info(f"Revert: Restored original content for '{abs_p}'")
                        except Exception as e:
                            logger.warning(f"Failed to restore file snapshot for '{path_str}': {e}")
                except Exception as e:
                    logger.warning(f"Failed to read snapshot metadata in '{k_dir}': {e}")

            # Clean up revert checkpoint directory from disk
            shutil.rmtree(k_dir, ignore_errors=True)

        return restored_any

    def clear_session(self, session_id: str) -> None:
        """Clear all stored snapshots for a given session ID."""
        if not session_id:
            return
        session_dir = get_snapshots_dir() / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    def clear(self) -> None:
        """Clear all stored snapshots."""
        shutil.rmtree(get_snapshots_dir(), ignore_errors=True)
