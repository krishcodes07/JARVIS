"""
JARVIS Central Path Management — Centralized path resolution for user home (~/.jarvis)
and workspace directories.

All subsystems (sessions, memory, vector store, logs, cache, GUI, skills) retrieve
their storage paths through these centralized helper functions.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Project repository root directory
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_jarvis_home() -> Path:
    """Get the JARVIS user home directory path (~/.jarvis or $JARVIS_HOME)."""
    env_home = os.getenv("JARVIS_HOME")
    if env_home:
        return Path(env_home).resolve()
    return (Path.home() / ".jarvis").resolve()


# Core Home & Workspace Root Paths
JARVIS_HOME = get_jarvis_home()
JARVIS_CONFIG_DIR = JARVIS_HOME / "config"
JARVIS_WORKSPACE_DIR = JARVIS_HOME / "workspace"


# ─── Subsystem Workspace Directory Helpers ───────────────────

def get_sessions_dir() -> Path:
    """Get the path to the conversation sessions directory (~/.jarvis/workspace/sessions)."""
    d = get_jarvis_home() / "workspace" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_snapshots_dir() -> Path:
    """Get the path to the file snapshots directory (~/.jarvis/workspace/snapshots)."""
    d = get_jarvis_home() / "workspace" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_long_term_memory_dir() -> Path:
    """Get the path to the long-term memory directory (~/.jarvis/workspace/long_term_memory)."""
    d = get_jarvis_home() / "workspace" / "long_term_memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_vector_store_dir() -> Path:
    """Get the path to the vector store directory (~/.jarvis/workspace/vector_store)."""
    d = get_jarvis_home() / "workspace" / "vector_store"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_knowledge_base_dir() -> Path:
    """Get the path to the knowledge base directory (~/.jarvis/workspace/knowledge_base)."""
    d = get_jarvis_home() / "workspace" / "knowledge_base"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logs_dir() -> Path:
    """Get the path to the log files directory (~/.jarvis/workspace/logs)."""
    d = get_jarvis_home() / "workspace" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_cache_dir() -> Path:
    """Get the path to the cache directory (~/.jarvis/workspace/cache)."""
    d = get_jarvis_home() / "workspace" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_gui_dir() -> Path:
    """Get the path to the GUI storage directory (~/.jarvis/workspace/gui)."""
    d = get_jarvis_home() / "workspace" / "gui"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_user_skills_dir() -> Path:
    """Get the path to user custom skills directory (~/.jarvis/workspace/skills)."""
    d = get_jarvis_home() / "workspace" / "skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_data_path(path_input: str | Path) -> Path:
    """Resolve any data or storage path relative to ~/.jarvis/workspace.

    Handles legacy path strings such as 'data/conversations', 'workspace/sessions', etc.
    """
    path_obj = Path(path_input)
    if path_obj.is_absolute():
        return path_obj

    clean_str = str(path_input).replace("\\", "/")
    if clean_str.startswith("workspace/conversations") or clean_str.startswith("data/conversations") or clean_str.startswith("workspace/sessions"):
        return get_sessions_dir()
    if clean_str.startswith("workspace/"):
        clean_str = clean_str[10:]
    elif clean_str.startswith("data/"):
        clean_str = clean_str[5:]

    res_dir = get_jarvis_home() / "workspace" / clean_str
    res_dir.parent.mkdir(parents=True, exist_ok=True)
    return res_dir


def sync_legacy_sessions() -> None:
    """Copy any legacy session files from repo data/conversations or data/sessions to ~/.jarvis/workspace/sessions."""
    target_dir = get_sessions_dir()

    legacy_dirs = [
        PROJECT_ROOT / "data" / "conversations",
        PROJECT_ROOT / "data" / "sessions",
        get_jarvis_home() / "workspace" / "conversations",
    ]

    for leg_dir in legacy_dirs:
        if leg_dir.exists() and leg_dir.is_dir():
            for p in leg_dir.glob("*.json"):
                dst = target_dir / p.name
                if not dst.exists():
                    try:
                        shutil.copy2(p, dst)
                        logger.info(f"Migrated legacy session file {p.name} to {dst}")
                    except Exception as e:
                        logger.warning(f"Failed migrating legacy session {p}: {e}")
