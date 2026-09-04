"""
Unit tests for memory stores (LongTermStore, ConversationStore).
"""

import pytest

from jarvis.core.config import ConversationMemoryConfig, LongTermMemoryConfig
from jarvis.memory.conversation.store import ConversationStore
from jarvis.memory.long_term.store import LongTermStore


@pytest.mark.asyncio
async def test_long_term_store_empty_file_recovery(tmp_path):
    memories_file = tmp_path / "long_term_memory" / "memories.json"
    memories_file.parent.mkdir(parents=True, exist_ok=True)
    # Create empty file
    memories_file.write_text("", encoding="utf-8")

    cfg = LongTermMemoryConfig(storage_path=str(tmp_path / "long_term_memory"))
    store = LongTermStore(cfg)
    store._storage_path = memories_file

    # Should not raise JSONDecodeError
    await store.initialize()
    assert store._memories == {}
    assert memories_file.read_text(encoding="utf-8") == "{}"

    # Store a memory
    await store.store("user_name", {"content": "Krish", "category": "fact"})
    assert "user_name" in store._memories


@pytest.mark.asyncio
async def test_conversation_store_empty_file_recovery(tmp_path):
    session_file = tmp_path / "test_session.json"
    session_file.write_text("", encoding="utf-8")

    cfg = ConversationMemoryConfig()
    store = ConversationStore(cfg)
    store._storage_dir = tmp_path

    loaded = await store._load_session("test_session")
    assert loaded == []
    assert session_file.read_text(encoding="utf-8") == "[]"


@pytest.mark.asyncio
async def test_long_term_store_get_and_delete(tmp_path):
    memories_file = tmp_path / "long_term_memory" / "memories.json"
    cfg = LongTermMemoryConfig(storage_path=str(tmp_path / "long_term_memory"))
    store = LongTermStore(cfg)
    store._storage_path = memories_file
    await store.initialize()

    # Get non-existent
    assert store.get("pref_theme") is None

    # Store and get
    await store.store("pref_theme", {"content": "User prefers dark mode", "category": "preference"})
    mem = store.get("pref_theme")
    assert mem is not None
    assert mem["key"] == "pref_theme"
    assert mem["content"] == "User prefers dark mode"

    # Delete existing
    await store.delete("pref_theme")
    assert store.get("pref_theme") is None

    # Verify persisted JSON
    import json
    disk_data = json.loads(memories_file.read_text(encoding="utf-8"))
    assert "pref_theme" not in disk_data

    # Delete non-existent (should complete without error)
    await store.delete("pref_theme")


@pytest.mark.asyncio
async def test_memory_manager_save_edit_delete(tmp_path):
    from unittest.mock import MagicMock
    from jarvis.core.config import JarvisConfig
    from jarvis.memory.manager import MemoryManager

    config = JarvisConfig()
    config.memory.long_term.enabled = True
    config.memory.long_term.storage_path = str(tmp_path / "long_term_memory")
    config.memory.conversation.enabled = False
    config.memory.vector.enabled = False

    manager = MemoryManager(config)
    await manager.initialize()
    assert manager.long_term is not None
    lt = manager.long_term

    # Save
    await manager.save_memory("user_city", "User lives in Seattle.", "fact")
    entry = lt.get("user_city")
    assert entry is not None
    assert entry["content"] == "User lives in Seattle."

    # Edit
    success = await manager.edit_memory("user_city", "User lives in San Francisco.", "fact")
    assert success is True
    updated = lt.get("user_city")
    assert updated is not None
    assert updated["content"] == "User lives in San Francisco."

    # Delete
    deleted = await manager.delete_memory("user_city")
    assert deleted is True
    assert lt.get("user_city") is None


@pytest.mark.asyncio
async def test_memory_manager_extract_and_store_dispatch(tmp_path):
    from unittest.mock import AsyncMock, patch
    from jarvis.core.config import JarvisConfig
    from jarvis.memory.manager import MemoryManager

    config = JarvisConfig()
    config.memory.long_term.enabled = True
    config.memory.long_term.storage_path = str(tmp_path / "long_term_memory")
    config.memory.conversation.enabled = False
    config.memory.vector.enabled = False

    manager = MemoryManager(config)
    await manager.initialize()
    assert manager.long_term is not None
    lt = manager.long_term

    # Pre-populate one memory to edit and one to delete
    await manager.save_memory("old_project", "Project Alpha in Go", "project")
    await manager.save_memory("pref_lang", "User prefers Python 3.10", "preference")

    # Mock provider
    mock_provider = AsyncMock()
    manager.set_provider_source(lambda: mock_provider)

    mock_operations = [
        {"action": "edit", "key": "pref_lang", "content": "User prefers Python 3.12", "category": "preference"},
        {"action": "delete", "key": "old_project"},
        {"action": "add", "key": "new_skill", "content": "User knows Rust.", "category": "fact"},
    ]

    with patch("jarvis.memory.long_term.extractor.MemoryExtractor.extract", AsyncMock(return_value=mock_operations)):
        applied = await manager.extract_and_store("session_123", [{"role": "user", "content": "Updates"}])

    assert len(applied) == 3
    # Check edit
    pref_entry = lt.get("pref_lang")
    assert pref_entry is not None
    assert pref_entry["content"] == "User prefers Python 3.12"
    # Check delete
    assert lt.get("old_project") is None
    # Check add
    skill_entry = lt.get("new_skill")
    assert skill_entry is not None
    assert skill_entry["content"] == "User knows Rust."
