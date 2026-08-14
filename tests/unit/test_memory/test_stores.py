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
