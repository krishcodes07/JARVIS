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

