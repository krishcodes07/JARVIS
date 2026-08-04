"""
JARVIS — Test Configuration and Shared Fixtures.
"""

import pytest


@pytest.fixture
def sample_config():
    """Create a sample JarvisConfig for testing."""
    from jarvis.core.config import JarvisConfig
    return JarvisConfig()


@pytest.fixture
def sample_messages():
    """Create sample conversation messages."""
    from jarvis.providers.base import Message
    return [
        Message(role="system", content="You are JARVIS."),
        Message(role="user", content="Hello, JARVIS!"),
    ]
