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


def test_google_provider_thought_signature():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    raw_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {"name": "list_directory", "args": {"path": "D:\\coding"}},
                            "thought_signature": "sig_abc123token",
                        }
                    ]
                }
            }
        ]
    }

    parsed = google_p._parse_response(raw_response)
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0]["thought_signature"] == "sig_abc123token"

    # Now verify _format_contents retains thought_signature
    messages = [
        Message(
            role="assistant",
            content="",
            tool_calls=parsed.tool_calls,
        )
    ]

    _, contents = google_p._format_contents(messages)
    assert len(contents) == 1
    assert contents[0]["parts"][0]["thoughtSignature"] == "sig_abc123token"
    assert "thought_signature" not in contents[0]["parts"][0]["functionCall"]


def test_google_provider_clean_schema():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "search_tool",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "title": "Query String", "default": "hello"},
            "opt": {
                "anyOf": [{"type": "integer"}, {"type": "null"}],
                "description": "optional number",
            },
        },
    }

    cleaned = google_p._clean_schema(schema)

    assert "$schema" not in cleaned
    assert "title" not in cleaned
    assert "additionalProperties" not in cleaned
    assert cleaned["type"] == "OBJECT"
    assert "type" not in cleaned["properties"]
    assert cleaned["properties"]["query"]["type"] == "STRING"
    assert "title" not in cleaned["properties"]["query"]
    assert "default" not in cleaned["properties"]["query"]
    assert cleaned["properties"]["opt"]["type"] == "INTEGER"
    assert cleaned["properties"]["opt"]["nullable"] is True


def test_anthropic_provider_format_messages():
    anthropic_p = AnthropicProvider(api_key="test", base_url="https://api.anthropic.com")

    messages = [
        Message(role="system", content="System instruction"),
        Message(role="user", content="What is 2+2?"),
        Message(
            role="assistant",
            content="",
            tool_calls=[{
                "id": "tool_123",
                "type": "function",
                "function": {"name": "calc", "arguments": '{"expr": "2+2"}'},
            }],
        ),
        Message(role="tool", name="calc", content="4", tool_call_id="tool_123"),
        Message(role="assistant", content="The answer is 4."),
    ]

    sys_prompt, formatted = anthropic_p._split_system(messages)
    assert sys_prompt == "System instruction"
    assert len(formatted) == 4

    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"] == "What is 2+2?"

    # Assistant turn with tool_use
    assert formatted[1]["role"] == "assistant"
    assert isinstance(formatted[1]["content"], list)
    assert formatted[1]["content"][0]["type"] == "tool_use"
    assert formatted[1]["content"][0]["id"] == "tool_123"
    assert formatted[1]["content"][0]["name"] == "calc"
    assert formatted[1]["content"][0]["input"] == {"expr": "2+2"}

    # User turn with tool_result
    assert formatted[2]["role"] == "user"
    assert isinstance(formatted[2]["content"], list)
    assert formatted[2]["content"][0]["type"] == "tool_result"
    assert formatted[2]["content"][0]["tool_use_id"] == "tool_123"
    assert formatted[2]["content"][0]["content"] == "4"

    # Final assistant turn
    assert formatted[3]["role"] == "assistant"
    assert formatted[3]["content"] == "The answer is 4."


def test_openai_provider_format_messages():
    openai_p = OpenAIProvider(api_key="test", base_url="https://api.openai.com/v1")

    assistant_msg = Message(
        role="assistant",
        content="",
        tool_calls=[{
            "id": "call_1",
            "type": "function",
            "function": {"name": "search", "arguments": '{"q": "test"}'},
        }],
    )
    formatted_assistant = openai_p._format_message(assistant_msg)
    assert formatted_assistant["role"] == "assistant"
    assert formatted_assistant["content"] is None
    assert formatted_assistant["tool_calls"] == assistant_msg.tool_calls

    tool_msg = Message(role="tool", name="search", content="search results", tool_call_id="call_1")
    formatted_tool = openai_p._format_message(tool_msg)
    assert formatted_tool["role"] == "tool"
    assert formatted_tool["content"] == "search results"
    assert formatted_tool["tool_call_id"] == "call_1"
    assert formatted_tool["name"] == "search"


def test_google_provider_multiple_tool_merging():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")

    messages = [
        Message(role="system", content="Sys"),
        Message(role="user", content="Run two tools"),
        Message(
            role="assistant",
            content="",
            tool_calls=[
                {"id": "c1", "type": "function", "function": {"name": "tool1", "arguments": "{}"}},
                {"id": "c2", "type": "function", "function": {"name": "tool2", "arguments": "{}"}},
            ],
        ),
        Message(role="tool", name="tool1", content="res1", tool_call_id="c1"),
        Message(role="tool", name="tool2", content="res2", tool_call_id="c2"),
    ]

    _, contents = google_p._format_contents(messages)
    # user turn, model turn, merged user tool turn
    assert len(contents) == 3
    assert contents[2]["role"] == "user"
    assert len(contents[2]["parts"]) == 2
    assert contents[2]["parts"][0]["functionResponse"]["name"] == "tool1"
    assert contents[2]["parts"][1]["functionResponse"]["name"] == "tool2"


def test_openai_provider_reasoning_parsing():
    openai_p = OpenAIProvider(api_key="test", base_url="https://api.openai.com/v1")
    raw = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello world!",
                    "reasoning_content": "User said hi. I will greet them.",
                },
                "finish_reason": "stop",
            }
        ]
    }
    resp = openai_p._parse_response(raw)
    assert "<think>" in resp.content
    assert "User said hi. I will greet them." in resp.content
    assert "</think>" in resp.content
    assert "Hello world!" in resp.content


def test_anthropic_provider_thinking_parsing():
    anthropic_p = AnthropicProvider(api_key="test", base_url="https://api.anthropic.com")
    raw = {
        "content": [
            {"type": "thinking", "thinking": "Internal analysis of the problem..."},
            {"type": "text", "text": "Here is the final answer."},
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
    resp = anthropic_p._parse_response(raw)
    assert "<think>" in resp.content
    assert "Internal analysis of the problem..." in resp.content
    assert "</think>" in resp.content
    assert "Here is the final answer." in resp.content


def test_google_provider_thought_parsing():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")
    raw = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Gemini internal reasoning...", "thought": True},
                        {"text": "Direct response to user."},
                    ]
                },
                "finishReason": "STOP",
            }
        ]
    }
    resp = google_p._parse_response(raw)
    assert "<think>" in resp.content
    assert "Gemini internal reasoning..." in resp.content
    assert "</think>" in resp.content
    assert "Direct response to user." in resp.content


def test_openai_payload_thinking_toggle_and_reasoning_options():
    openai_p = OpenAIProvider(api_key="test", base_url="https://api.openai.com/v1")
    msgs = [Message(role="user", content="hello")]

    # 1. Configurable reasoning model with effort (e.g. gpt-5.5) and thinking=True
    cfg_on = GenerationConfig(model="gpt-5.5", thinking=True, reasoning_effort="high")
    payload_on = openai_p._build_payload(msgs, cfg_on)
    assert payload_on.get("reasoning_effort") == "high"

    # 2. Configurable reasoning model with effort that supports "none" (e.g. gpt-5.5) and thinking=False
    cfg_off = GenerationConfig(model="gpt-5.5", thinking=False)
    payload_off = openai_p._build_payload(msgs, cfg_off)
    assert payload_off.get("reasoning_effort") == "none"

    # 3. Only-thinking model (e.g. deepseek-reasoner) when thinking=False: does not pass reasoning_effort or reasoning=False
    cfg_only_off = GenerationConfig(model="deepseek-reasoner", provider_id="deepseek", thinking=False)
    payload_only_off = openai_p._build_payload(msgs, cfg_only_off)
    assert "reasoning_effort" not in payload_only_off
    assert payload_only_off.get("reasoning") is not False

    # 4. Standard non-reasoning model (e.g. llama-3.3-70b-versatile)
    cfg_standard = GenerationConfig(model="llama-3.3-70b-versatile", thinking=False)
    payload_standard = openai_p._build_payload(msgs, cfg_standard)
    assert "reasoning_effort" not in payload_standard
    assert "reasoning" not in payload_standard

    # 5. OpenRouter provider sends reasoning as an object
    openrouter_p = OpenAIProvider(api_key="test", base_url="https://openrouter.ai/api/v1")
    cfg_openrouter = GenerationConfig(model="gpt-5.5", provider_id="openrouter", thinking=True, reasoning_effort="high")
    payload_openrouter = openrouter_p._build_payload(msgs, cfg_openrouter)
    assert payload_openrouter.get("reasoning") == {"effort": "high"}
    assert "reasoning_effort" not in payload_openrouter

    # 6. Max tokens clamping
    cfg_huge = GenerationConfig(model="llama-3.3-70b-versatile", max_tokens=262144)
    payload_huge = openai_p._build_payload(msgs, cfg_huge)
    assert payload_huge["max_tokens"] <= 16384


def test_anthropic_payload_thinking_toggle():
    anthropic_p = AnthropicProvider(api_key="test", base_url="https://api.anthropic.com")
    msgs = [{"role": "user", "content": "hello"}]

    # 1. Configurable model (claude-opus-4-7 / claude-sonnet-5) with thinking=True
    cfg_on = GenerationConfig(model="claude-opus-4-7", provider_id="anthropic", thinking=True, thinking_budget=2048)
    payload_on = anthropic_p._build_payload("system", msgs, cfg_on)
    assert "thinking" in payload_on
    assert payload_on["thinking"]["type"] == "enabled"
    assert payload_on["thinking"]["budget_tokens"] == 2048
    assert payload_on["max_tokens"] > 2048

    # 2. Configurable model with thinking=False -> thinking omitted
    cfg_off = GenerationConfig(model="claude-opus-4-7", provider_id="anthropic", thinking=False)
    payload_off = anthropic_p._build_payload("system", msgs, cfg_off)
    assert "thinking" not in payload_off


def test_google_payload_thinking_toggle():
    google_p = GoogleProvider(api_key="test", base_url="https://generativelanguage.googleapis.com/v1beta")
    msgs = [Message(role="user", content="hello")]

    # 1. Configurable reasoning model (gemini-flash-lite-latest) with thinking=False
    cfg_off = GenerationConfig(model="gemini-flash-lite-latest", provider_id="google", thinking=False)
    sys_inst, contents = google_p._format_contents(msgs)
    payload_off = google_p._build_payload(sys_inst, contents, cfg_off)
    assert payload_off["generationConfig"].get("thinkingConfig") == {"thinkingBudget": 0}

    # 2. Only-thinking model with thinking=False -> does not force thinkingBudget: 0
    cfg_only_off = GenerationConfig(model="gemini-3.1-flash-tts-preview", provider_id="google", thinking=False)
    payload_only_off = google_p._build_payload(sys_inst, contents, cfg_only_off)
    assert "thinkingConfig" not in payload_only_off["generationConfig"]




