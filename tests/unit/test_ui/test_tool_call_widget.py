"""
Unit tests for ToolCallWidget, MessageWidget error sanitization, and LLM provider tool message formatting.
"""

from __future__ import annotations

import json
import pytest
from textual.app import App

from jarvis.providers.base import Message
from jarvis.providers.protocols.anthropic import AnthropicProvider
from jarvis.providers.protocols.google import GoogleProvider
from jarvis.providers.protocols.openai import OpenAIProvider
from jarvis.ui.tui.widgets.chat_view import MessageWidget, ToolCallWidget


class WidgetTestApp(App):
    def compose(self):
        yield ToolCallWidget(tool_name="list_tools", args_str="query='test'")
        yield MessageWidget(content="test", role="assistant")


@pytest.mark.asyncio
async def test_tool_call_widget_initial_state():
    app = WidgetTestApp()
    async with app.run_test():
        widget = app.query_one(ToolCallWidget)
        header_text = str(widget._format_header())
        assert "▸" in header_text
        assert "List Tools" in header_text
        assert "query='test'" in header_text
        assert widget._expanded is False
        assert "expanded" not in widget.output_widget.classes


@pytest.mark.asyncio
async def test_tool_call_widget_toggle_and_output():
    class CustomApp(App):
        def compose(self):
            yield ToolCallWidget(tool_name="list_tools", args_str="")

    app = CustomApp()
    async with app.run_test():
        widget = app.query_one(ToolCallWidget)
        # Toggle before output is set
        widget.toggle_expanded()
        assert widget._expanded is True
        assert "expanded" in widget.output_widget.classes
        header_text = str(widget._format_header())
        assert "▾" in header_text
        output_text = str(widget.output_widget.render())
        assert "executing tool" in output_text

        # Set output
        widget.set_output("append_file, browser_control, click_element")
        assert widget.result_text == "append_file, browser_control, click_element"
        output_text_after = str(widget.output_widget.render())
        assert "append_file, browser_control" in output_text_after

        # Collapse
        widget.toggle_expanded()
        assert widget._expanded is False
        assert "expanded" not in widget.output_widget.classes
        header_text_collapsed = str(widget._format_header())
        assert "▸" in header_text_collapsed


@pytest.mark.asyncio
async def test_tool_call_widget_truncation():
    class CustomApp(App):
        def compose(self):
            yield ToolCallWidget(tool_name="large_output_tool", args_str="")

    app = CustomApp()
    async with app.run_test():
        widget = app.query_one(ToolCallWidget)
        giant_output = "A" * 20000
        widget.set_output(giant_output)
        rendered = str(widget.output_widget.render())
        assert "(output truncated)" in rendered
        assert len(rendered) < 15000


@pytest.mark.asyncio
async def test_message_widget_error_sanitization():
    class ErrorApp(App):
        def compose(self):
            yield MessageWidget(content="Invalid parameters provided", role="error", id="msg1")
            yield MessageWidget(content="Error: Something failed", role="error", id="msg2")
            yield MessageWidget(content="❌ Error: Error: API timeout", role="error", id="msg3")
            yield MessageWidget(content="", role="error", id="msg4")
            yield MessageWidget(content="   ", role="error", id="msg5")

    app = ErrorApp()
    async with app.run_test():
        msg1 = app.query_one("#msg1", MessageWidget)
        assert "❌ Error: Invalid parameters provided" in str(msg1.render())

        msg2 = app.query_one("#msg2", MessageWidget)
        assert "❌ Error: Something failed" in str(msg2.render())
        assert "Error: Error:" not in str(msg2.render())

        msg3 = app.query_one("#msg3", MessageWidget)
        assert "❌ Error: API timeout" in str(msg3.render())
        assert "❌ Error: ❌" not in str(msg3.render())

        msg4 = app.query_one("#msg4", MessageWidget)
        assert "❌ Error: Request interrupted or an unexpected error occurred." in str(msg4.render())

        msg5 = app.query_one("#msg5", MessageWidget)
        assert "❌ Error: Request interrupted or an unexpected error occurred." in str(msg5.render())


def test_openai_format_message_with_thinking_and_tools():
    provider = OpenAIProvider(api_key="test-key", base_url="https://api.openai.com/v1")

    # Assistant message with only thinking and tool calls -> content should be None
    msg_thinking_only = Message(
        role="assistant",
        content="<think>\nLet me check available tools first.\n</think>\n",
        tool_calls=[{
            "id": "call_123",
            "type": "function",
            "function": {"name": "list_tools", "arguments": "{}"},
        }],
    )
    formatted = provider._format_message(msg_thinking_only)
    assert formatted["role"] == "assistant"
    assert formatted["content"] is None
    assert formatted["tool_calls"] == msg_thinking_only.tool_calls

    # Assistant message with thinking AND real content alongside tool calls
    msg_with_text = Message(
        role="assistant",
        content="<think>\nSearching repository...\n</think>\nChecking your repository now.",
        tool_calls=[{
            "id": "call_456",
            "type": "function",
            "function": {"name": "github_repos", "arguments": "{}"},
        }],
    )
    formatted_text = provider._format_message(msg_with_text)
    assert formatted_text["role"] == "assistant"
    assert formatted_text["content"] == "Checking your repository now."
    assert "<think>" not in formatted_text["content"]
    assert formatted_text["tool_calls"] == msg_with_text.tool_calls


def test_anthropic_format_message_with_thinking_and_tools():
    provider = AnthropicProvider(api_key="test-key", base_url="https://api.anthropic.com")
    msg = Message(
        role="assistant",
        content="<think>\nEvaluating tools\n</think>\nI am looking at your repos.",
        tool_calls=[{
            "id": "call_789",
            "type": "function",
            "function": {"name": "list_tools", "arguments": json.dumps({})},
        }],
    )
    formatted = provider._format_message(msg)
    blocks = formatted["content"]
    assert len(blocks) == 2
    assert blocks[0]["type"] == "text"
    assert blocks[0]["text"] == "I am looking at your repos."
    assert "<think>" not in blocks[0]["text"]
    assert blocks[1]["type"] == "tool_use"
    assert blocks[1]["name"] == "list_tools"


def test_google_format_message_with_thinking_and_tools():
    provider = GoogleProvider(api_key="test-key", base_url="https://generativelanguage.googleapis.com")
    messages = [
        Message(
            role="assistant",
            content="<think>\nChecking github\n</think>\nListing tools now.",
            tool_calls=[{
                "id": "call_abc",
                "type": "function",
                "function": {"name": "list_tools", "arguments": json.dumps({})},
            }],
        )
    ]
    _, contents = provider._format_contents(messages)
    assert len(contents) == 1
    parts = contents[0]["parts"]
    assert any(p.get("text") == "Listing tools now." for p in parts)
    assert not any("<think>" in p.get("text", "") for p in parts)
