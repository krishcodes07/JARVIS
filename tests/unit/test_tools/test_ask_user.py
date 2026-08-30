"""
Unit tests for AskUserTool.
"""

import pytest
from jarvis.core.config import JarvisConfig
from jarvis.tools.basic.ask_user import AskUserTool, _normalize_questions


@pytest.mark.asyncio
async def test_ask_user_schema():
    config = JarvisConfig()
    tool = AskUserTool()
    tool.configure(config)

    assert tool.name == "ask_user"
    assert "ask" in tool.description.lower()
    param_names = [p.name for p in tool.schema.parameters]
    assert "questions" in param_names
    assert "question" in param_names
    assert "options" in param_names
    assert "is_multi_select" in param_names


def test_normalize_questions_single():
    res = _normalize_questions({
        "question": "Which database?",
        "options": ["PostgreSQL", "SQLite"],
        "title": "DB Choice",
    })
    assert len(res) == 1
    assert res[0]["question"] == "Which database?"
    assert res[0]["options"] == ["PostgreSQL", "SQLite"]
    assert res[0]["header"] == "DB Choice"


def test_normalize_questions_multiple():
    res = _normalize_questions({
        "questions": [
            {"question": "Q1", "options": ["A", "B"]},
            {"question": "Q2", "options": ["C", "D"], "is_multi_select": True},
        ]
    })
    assert len(res) == 2
    assert res[0]["question"] == "Q1"
    assert res[0]["options"] == ["A", "B"]
    assert res[1]["question"] == "Q2"
    assert res[1]["is_multi_select"] is True


@pytest.mark.asyncio
async def test_ask_user_with_callback():
    tool = AskUserTool()

    async def mock_callback(questions):
        assert len(questions) == 1
        assert questions[0]["question"] == "Choose styling:"
        return "Tailwind CSS"

    res = await tool.execute(
        question="Choose styling:",
        options=["Tailwind CSS", "Vanilla CSS"],
        ask_user_callback=mock_callback,
    )
    assert "User response to 'Choose styling:': Tailwind CSS" in res


@pytest.mark.asyncio
async def test_ask_user_multiple_questions_callback():
    tool = AskUserTool()

    async def mock_callback(questions):
        assert len(questions) == 2
        return {
            "Select architecture:": "Microservices",
            "Enable caching:": "Redis",
        }

    res = await tool.execute(
        questions=[
            {"question": "Select architecture:", "options": ["Monolith", "Microservices"]},
            {"question": "Enable caching:", "options": ["Redis", "Memcached"]},
        ],
        ask_user_callback=mock_callback,
    )
    assert "Select architecture:: Microservices" in res
    assert "Enable caching:: Redis" in res


@pytest.mark.asyncio
async def test_ask_user_non_interactive_fallback():
    tool = AskUserTool()
    res = await tool.execute(
        question="Select runtime:",
        options=["Node.js", "Python", "Go"],
    )
    assert "User responses (automated fallback):" in res
    assert "Select runtime:: Node.js" in res


@pytest.mark.asyncio
async def test_ask_user_no_question_error():
    tool = AskUserTool()
    res = await tool.execute()
    assert "Error: No question provided" in res
