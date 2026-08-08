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


def test_google_provider_format_contents():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    messages = [
        Message(role="system", content="System prompt"),
        Message(role="user", content="Hello"),
        Message(
            role="assistant",
            content="",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {"name": "calculator", "arguments": '{"a": 1, "b": 2}'},
            }],
        ),
        Message(role="tool", name="calculator", content="3", tool_call_id="call_1"),
    ]

    sys_inst, contents = google_p._format_contents(messages)

    assert sys_inst == "System prompt"
    assert len(contents) == 3

    # User turn
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"] == [{"text": "Hello"}]

    # Assistant turn with tool call
    assert contents[1]["role"] == "model"
    assert len(contents[1]["parts"]) == 1
    assert "functionCall" in contents[1]["parts"][0]
    assert contents[1]["parts"][0]["functionCall"]["name"] == "calculator"
    assert contents[1]["parts"][0]["functionCall"]["args"] == {"a": 1, "b": 2}

    # Tool result turn
    assert contents[2]["role"] == "user"
    assert len(contents[2]["parts"]) == 1
    assert "functionResponse" in contents[2]["parts"][0]
    assert contents[2]["parts"][0]["functionResponse"]["name"] == "calculator"
    assert contents[2]["parts"][0]["functionResponse"]["response"] == {
        "name": "calculator",
        "content": "3",
    }


def test_google_provider_clean_schema():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "query": {"type": "string", "title": "Query String"}
        },
    }

    cleaned = google_p._clean_schema(schema)

    assert "$schema" not in cleaned
    assert cleaned["type"] == "OBJECT"
    assert cleaned["properties"]["query"]["type"] == "STRING"
    assert "title" not in cleaned["properties"]["query"]

