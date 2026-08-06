from jarvis.providers.base import GenerationConfig, Message
from jarvis.providers.protocols.anthropic import AnthropicProvider
from jarvis.providers.protocols.google import GoogleProvider
from jarvis.providers.protocols.openai import OpenAIProvider


def test_provider_stream_type_compatibility():
    # Verify that stream method on subclasses produces an AsyncIterator
    openai_p = OpenAIProvider(api_key="test", base_url="https://api.openai.com/v1")
    anthropic_p = AnthropicProvider(api_key="test", base_url="https://api.anthropic.com")
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    cfg = GenerationConfig(model="test")
    msgs = [Message(role="user", content="hi")]

    # Stream returns AsyncIterator (async generator), not a Coroutine
    res_openai = openai_p.stream(msgs, cfg)
    res_anthropic = anthropic_p.stream(msgs, cfg)
    res_google = google_p.stream(msgs, cfg)

    assert hasattr(res_openai, "__aiter__")
    assert hasattr(res_anthropic, "__aiter__")
    assert hasattr(res_google, "__aiter__")
