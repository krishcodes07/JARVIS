"""
Unit tests for MemoryExtractor: add, edit, and delete operations.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from jarvis.memory.long_term.extractor import MemoryExtractionError, MemoryExtractor
from jarvis.providers.base import BaseProvider, GenerationConfig, GenerationResponse, Message


class DummyProvider(BaseProvider):
    """Mock provider returning predefined content."""

    def __init__(self, response_content: str = "[]") -> None:
        super().__init__(api_key="test", base_url="http://test")
        self.response_content = response_content
        self.last_messages: list[Message] = []

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResponse:
        self.last_messages = messages
        return GenerationResponse(content=self.response_content)

    async def stream(self, messages, config):
        yield self.response_content

    async def embed(self, texts, model):
        return [[0.1, 0.2] for _ in texts]

    async def list_models(self):
        return [{"id": "dummy", "name": "dummy"}]


def test_parse_response_array():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    raw = """
    [
      {"action": "add", "key": "fav_color", "content": "User loves blue.", "category": "preference"},
      {"action": "edit", "key": "user_city", "content": "User lives in Berlin.", "category": "fact"},
      {"action": "delete", "key": "old_project"}
    ]
    """
    ops = extractor._parse_response(raw)
    assert len(ops) == 3
    assert ops[0] == {
        "action": "add",
        "key": "fav_color",
        "content": "User loves blue.",
        "category": "preference",
    }
    assert ops[1] == {
        "action": "edit",
        "key": "user_city",
        "content": "User lives in Berlin.",
        "category": "fact",
    }
    assert ops[2] == {
        "action": "delete",
        "key": "old_project",
    }


def test_parse_response_grouped_dict():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    raw = """
    {
      "add": [
        {"key": "favorite_food", "content": "User loves ramen.", "category": "preference"}
      ],
      "edit": [
        {"key": "job_title", "content": "User is a Staff Engineer.", "category": "fact"}
      ],
      "delete": [
        {"key": "legacy_task"}
      ]
    }
    """
    ops = extractor._parse_response(raw)
    assert len(ops) == 3
    assert ops[0]["action"] == "add"
    assert ops[0]["key"] == "favorite_food"
    assert ops[1]["action"] == "edit"
    assert ops[1]["key"] == "job_title"
    assert ops[2]["action"] == "delete"
    assert ops[2]["key"] == "legacy_task"


def test_parse_response_delete_string_keys():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    raw = """
    {
      "delete": ["project_alpha", "temp_notes"]
    }
    """
    ops = extractor._parse_response(raw)
    assert len(ops) == 2
    assert ops[0] == {"action": "delete", "key": "project_alpha"}
    assert ops[1] == {"action": "delete", "key": "temp_notes"}


def test_parse_response_aliases_and_markdown_fence():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    raw = """```json
    [
      {"action": "update", "key": "user_theme", "content": "User switched to light theme.", "category": "preference"},
      {"action": "remove", "key": "old_car"},
      {"action": "create", "key": "new_hobby", "content": "User started rock climbing."}
    ]
    ```"""
    ops = extractor._parse_response(raw)
    assert len(ops) == 3
    assert ops[0]["action"] == "edit"
    assert ops[1]["action"] == "delete"
    assert ops[2]["action"] == "add"


def test_parse_response_default_fallback():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    # Legacy output without action field
    raw = '[{"key": "editor", "content": "User uses VS Code.", "category": "preference"}]'
    ops = extractor._parse_response(raw)
    assert len(ops) == 1
    assert ops[0]["action"] == "add"
    assert ops[0]["key"] == "editor"


def test_parse_response_invalid_entries_skipped():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    raw = """
    [
      {"action": "edit", "key": "", "content": "No key"},
      {"action": "edit", "key": "valid_key", "content": ""},
      {"action": "delete", "key": ""},
      {"action": "add", "key": "ok_key", "content": "Valid content"}
    ]
    """
    ops = extractor._parse_response(raw)
    assert len(ops) == 1
    assert ops[0]["action"] == "add"
    assert ops[0]["key"] == "ok_key"


def test_parse_response_empty():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    assert extractor._parse_response("") == []
    assert extractor._parse_response("[]") == []
    assert extractor._parse_response("not a valid json") == []


def test_parse_response_extra_trailing_text_and_thinking_tags():
    extractor = MemoryExtractor(DummyProvider(), "dummy-model")
    # Empty array with trailing text (previously failed with Extra data: line 1 column 3)
    raw_empty_extra = "[]\nNo memories found in this conversation."
    assert extractor._parse_response(raw_empty_extra) == []

    # Valid array with trailing explanation (previously failed with Extra data: line 3 column 1)
    raw_extra = """[
      {"action": "add", "key": "user_city", "content": "User lives in Seattle.", "category": "fact"}
    ]
    [Note: I recorded that the user moved to Seattle.]"""
    ops = extractor._parse_response(raw_extra)
    assert len(ops) == 1
    assert ops[0]["key"] == "user_city"

    # Reasoning model with <think>...</think> tags
    raw_think = """<think>
    The user mentioned they use Neovim. This is a durable preference.
    </think>
    [{"action": "add", "key": "fav_editor", "content": "User uses Neovim.", "category": "preference"}]"""
    ops2 = extractor._parse_response(raw_think)
    assert len(ops2) == 1
    assert ops2[0]["key"] == "fav_editor"


@pytest.mark.asyncio
async def test_extract_formats_existing_memories():
    provider = DummyProvider("[]")
    extractor = MemoryExtractor(provider, "test-model")

    existing = [
        {"key": "city", "content": "User lives in New York.", "category": "fact"},
        {"key": "theme", "content": "Dark mode.", "category": "preference"},
    ]
    messages = [{"role": "user", "content": "Actually I moved to Chicago."}]
    await extractor.extract(messages, existing_memories=existing)

    assert len(provider.last_messages) == 2
    sys_prompt = provider.last_messages[0].content
    assert "- key: city [fact] -> User lives in New York." in sys_prompt
    assert "- key: theme [preference] -> Dark mode." in sys_prompt


@pytest.mark.asyncio
async def test_extract_provider_error_raises_memory_extraction_error():
    provider = DummyProvider()
    provider.generate = AsyncMock(side_effect=RuntimeError("API quota exceeded"))
    extractor = MemoryExtractor(provider, "test-model")

    with pytest.raises(MemoryExtractionError) as exc_info:
        await extractor.extract([{"role": "user", "content": "Remember this."}])

    assert "API quota exceeded" in str(exc_info.value)
