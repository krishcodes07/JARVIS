import pytest
from textual.app import App

from jarvis.ui.tui.widgets.chat_view import (
    ChatViewWidget,
    MessageWidget,
    ThoughtWidget,
    ToolCallWidget,
)


class ChatTestApp(App):
    def compose(self):
        yield ChatViewWidget()


@pytest.mark.asyncio
async def test_thought_widget_states():
    class ThoughtApp(App):
        def compose(self):
            yield ThoughtWidget()

    app = ThoughtApp()
    async with app.run_test():
        tw = app.query_one(ThoughtWidget)
        assert tw._is_finished is False
        assert tw._expanded is False

        header_text = str(tw._format_header())
        assert "Thinking" in header_text

        # Append thoughts
        tw.append_chunk("Analyzing database structure...")
        assert tw.raw_thought == "Analyzing database structure..."

        # Finish thought
        tw.finish(elapsed_str="1.5s")
        assert tw._is_finished is True
        assert tw._elapsed_str == "1.5s"
        finished_header = str(tw._format_header())
        assert "Thought (1.5s)" in finished_header
        assert "▸" in finished_header

        # Toggle expansion
        tw.toggle_expanded()
        assert tw._expanded is True
        expanded_header = str(tw._format_header())
        assert "▾" in expanded_header
        assert "Thought (1.5s)" in expanded_header


@pytest.mark.asyncio
async def test_chat_view_think_stream_parsing():
    app = ChatTestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        chat.start_assistant_stream()

        # Stream chunks containing <think> ... </think> split across chunks
        chat.append_assistant_chunk("<th")
        chat.append_assistant_chunk("ink>I need to check the current directory.")
        chat.append_assistant_chunk("</th")
        chat.append_assistant_chunk("ink>Here are the files in your directory.")

        thought_widgets = [c for c in chat.children if isinstance(c, ThoughtWidget)]
        message_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "assistant"]

        assert len(thought_widgets) == 1
        assert thought_widgets[0].raw_thought == "I need to check the current directory."
        assert thought_widgets[0]._is_finished is True

        assert len(message_widgets) == 1
        assert "Here are the files in your directory." in message_widgets[0].raw_content


@pytest.mark.asyncio
async def test_chat_view_think_followed_by_tool_call():
    app = ChatTestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        chat.start_assistant_stream()

        # Model thinks and immediately calls tool without text outside <think>
        chat.append_assistant_chunk("<think>Searching for latest news...</think>")
        tool_w = chat.add_tool_call("web_search", 'query="AI news"')
        chat.add_tool_output("3 articles found.")

        thought_widgets = [c for c in chat.children if isinstance(c, ThoughtWidget)]
        tool_widgets = [c for c in chat.children if isinstance(c, ToolCallWidget)]
        assistant_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "assistant"]

        assert len(thought_widgets) == 1
        assert thought_widgets[0].raw_thought == "Searching for latest news..."
        assert thought_widgets[0]._is_finished is True

        assert len(tool_widgets) == 1
        assert tool_widgets[0].tool_name == "web_search"
        assert tool_widgets[0].result_text == "3 articles found."

        # Initial placeholder assistant message widget should be removed
        assert len(assistant_widgets) == 0


@pytest.mark.asyncio
async def test_chat_view_load_session_history_with_thoughts():
    app = ChatTestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        history = [
            {"role": "user", "content": "What is the weather?"},
            {
                "role": "assistant",
                "content": "<think>User wants weather info.</think>It is 22°C and sunny.",
                "model": "gemini-2.5-flash",
            },
        ]
        chat.load_session_history(history)

        thought_widgets = [c for c in chat.children if isinstance(c, ThoughtWidget)]
        user_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "user"]
        assistant_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "assistant"]

        assert len(user_widgets) == 1
        assert user_widgets[0].raw_content == "What is the weather?"

        assert len(thought_widgets) == 1
        assert thought_widgets[0].raw_thought == "User wants weather info."

        assert len(assistant_widgets) == 1
        assert assistant_widgets[0].raw_content == "It is 22°C and sunny."


def test_persona_thinking_toggle():
    from jarvis.core.config import ProviderConfig
    from jarvis.prompts.persona import get_persona

    # Default is thinking=True
    cfg = ProviderConfig()
    assert cfg.thinking is True

    persona_with_thinking = get_persona("professional_assistant", thinking=True)
    assert "## Thinking & Reasoning Rules" in persona_with_thinking
    assert "<think>...</think>" in persona_with_thinking

    persona_without_thinking = get_persona("professional_assistant", thinking=False)
    assert "## Thinking & Reasoning Rules" not in persona_without_thinking
    assert "<think>...</think>" not in persona_without_thinking
    assert "You are JARVIS" in persona_without_thinking


@pytest.mark.asyncio
async def test_chat_view_salted_think_tags():
    """Verify that salted tags like <think:6124c78e>...</think:6124c78e> are cleanly parsed."""
    app = ChatTestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        chat.start_assistant_stream()

        # Simulate streaming salted think tags as produced by reasoning models
        chat.append_assistant_chunk("<think:6124c78e>Checking rain alert status.")
        chat.append_assistant_chunk(" Weather data looks wet.</think:6124c78e>Yes, sir – there is a rain alert.")

        thought_widgets = [c for c in chat.children if isinstance(c, ThoughtWidget)]
        message_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "assistant"]

        assert len(thought_widgets) == 1
        assert thought_widgets[0].raw_thought == "Checking rain alert status. Weather data looks wet."
        assert thought_widgets[0]._is_finished is True

        assert len(message_widgets) == 1
        assert "Yes, sir – there is a rain alert." in message_widgets[0].raw_content
        # Ensure no tag suffix leaked into the message
        assert "6124c78e" not in message_widgets[0].raw_content
        assert "</think" not in message_widgets[0].raw_content


@pytest.mark.asyncio
async def test_chat_view_load_history_with_salted_think_tags():
    """Verify that history loading handles salted and variant think tags without tag leakage."""
    app = ChatTestApp()
    async with app.run_test():
        chat = app.query_one(ChatViewWidget)
        history = [
            {"role": "user", "content": "Weather in Haldwani?"},
            {
                "role": "assistant",
                "content": "<think:6124c78e>Analyzing Nainital district alert levels.</think:6124c78e>Yellow alert for heavy rainfall today.",
                "model": "tencent/hy3:free",
            },
        ]
        chat.load_session_history(history)

        thought_widgets = [c for c in chat.children if isinstance(c, ThoughtWidget)]
        assistant_widgets = [c for c in chat.children if isinstance(c, MessageWidget) and c.role == "assistant"]

        assert len(thought_widgets) == 1
        assert thought_widgets[0].raw_thought == "Analyzing Nainital district alert levels."

        assert len(assistant_widgets) == 1
        assert assistant_widgets[0].raw_content == "Yellow alert for heavy rainfall today."
        assert "6124c78e" not in assistant_widgets[0].raw_content

