"""
Integration test for JARVIS engine initialization.
"""

import pytest


class TestEngineIntegration:
    """Test the JARVIS engine initialization and lifecycle."""

    def test_engine_creation(self):
        """Engine can be instantiated."""
        from jarvis.core.engine import JarvisEngine
        engine = JarvisEngine()
        assert engine is not None
        assert not engine._initialized

    def test_config_loading(self):
        """Config loads with defaults when no file exists."""
        from jarvis.core.config import JarvisConfig
        config = JarvisConfig()
        assert config.jarvis.name == "JARVIS"
        assert config.jarvis.version == "0.1.0"
        assert config.provider.active == "groq"

    def test_constants(self):
        """Constants are properly defined."""
        from jarvis.core.constants import Protocol, Role, UIType
        assert Protocol.OPENAI == "openai"
        assert Role.USER == "user"
        assert UIType.TUI == "tui"

    @pytest.mark.asyncio
    async def test_memory_extraction_safely_handles_none_config(self):
        """Memory extraction methods do not crash if self.config is None."""
        from jarvis.core.engine import JarvisEngine
        engine = JarvisEngine()
        assert engine.config is None
        # Should return safely without raising AttributeError: 'NoneType' object has no attribute 'memory'
        await engine._extract_memories("session1", "hello", "hi")
        engine._schedule_memory_extraction("session1", "hello", "hi")

    def test_build_messages_from_history_with_tool_calls(self):
        """Engine reconstructs user, assistant with tool_calls, tool outputs, and assistant answers."""
        from jarvis.core.engine import JarvisEngine
        engine = JarvisEngine()

        history = [
            {"role": "user", "content": "Load coding skill"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_skill", "arguments": '{"skill_name": "coding"}'},
                }],
            },
            {
                "role": "tool",
                "content": "# Coding Skill\nWorkflow...",
                "tool_name": "get_skill",
                "tool_call_id": "call_1",
            },
            {"role": "assistant", "content": "I have loaded the coding skill."},
        ]

        messages = engine._build_messages_from_history(history, "You are JARVIS")

        assert len(messages) == 5
        assert messages[0].role == "system"
        assert messages[0].content == "You are JARVIS"

        assert messages[1].role == "user"
        assert messages[1].content == "Load coding skill"

        assert messages[2].role == "assistant"
        assert messages[2].tool_calls == history[1]["tool_calls"]

        assert messages[3].role == "tool"
        assert messages[3].content == "# Coding Skill\nWorkflow..."
        assert messages[3].name == "get_skill"
        assert messages[3].tool_call_id == "call_1"

        assert messages[4].role == "assistant"
        assert messages[4].content == "I have loaded the coding skill."

    def test_build_messages_from_history_legacy_tool_repair(self):
        """Engine synthesizes preceding assistant tool call if legacy history omitted it."""
        from jarvis.core.engine import JarvisEngine
        engine = JarvisEngine()

        history = [
            {"role": "user", "content": "What is in file.txt?"},
            {
                "role": "tool",
                "content": "file contents",
                "tool_name": "read_file",
                "tool_call_id": "call_read_file",
            },
            {"role": "assistant", "content": "The file contains: file contents"},
        ]

        messages = engine._build_messages_from_history(history, "Sys")

        assert len(messages) == 5
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        # Synthesized assistant tool call
        assert messages[2].role == "assistant"
        assert messages[2].tool_calls is not None
        assert messages[2].tool_calls[0]["function"]["name"] == "read_file"
        # Tool output
        assert messages[3].role == "tool"
        assert messages[3].content == "file contents"
        assert messages[4].role == "assistant"


