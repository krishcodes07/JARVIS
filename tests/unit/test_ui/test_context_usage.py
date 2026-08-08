"""
Unit tests for context window usage calculation, models.dev lookup, and status bar display.
"""

from __future__ import annotations

import pytest

from jarvis.providers.models_dev import get_model_context_limit
from jarvis.ui.tui.widgets.status_bar import StatusBarWidget, format_context_usage


def test_format_context_usage():
    """Test format_context_usage helper formatting."""
    # Under 1000 tokens
    assert format_context_usage(520, 204800) == "520 (0%)"
    # 5.5k tokens with 204800 context (~2.68% -> 3%)
    assert format_context_usage(5500, 204800) == "5.5k (3%)"
    # 12.3k tokens with 128000 context (~9.6% -> 10%)
    assert format_context_usage(12300, 128000) == "12.3k (10%)"
    # Large token count >= 100k
    assert format_context_usage(150000, 200000) == "150k (75%)"


def test_get_model_context_limit():
    """Test get_model_context_limit lookup from models.dev cache."""
    # GLM-5 has limit context 204800 in models.dev cache
    limit = get_model_context_limit("glm-5", "zhipuai")
    assert limit == 204800

    # Non-existent model should return default fallback 128000
    fallback_limit = get_model_context_limit("nonexistent-model-xyz")
    assert fallback_limit == 128000


def test_status_bar_context_usage_rendering():
    """Test StatusBarWidget rendering with and without context usage set."""
    widget = StatusBarWidget()
    assert widget.context_tokens is None
    assert widget.context_limit is None

    # Initial render should include "tab commands"
    rendered_initial = widget.render()
    assert "tab" in rendered_initial.plain
    assert "commands" in rendered_initial.plain

    # Set context usage
    widget.set_context_usage(5500, 204800)
    rendered_context = widget.render()
    assert "5.5k (3%)" in rendered_context.plain
    assert "tab commands" not in rendered_context.plain

    # Clear context usage
    widget.clear_context_usage()
    rendered_cleared = widget.render()
    assert "tab" in rendered_cleared.plain
    assert "commands" in rendered_cleared.plain


def test_sequential_context_updates():
    """Test sequential status bar updates as conversation turns increase."""
    widget = StatusBarWidget()

    # Message 1
    widget.set_context_usage(1800, 128000)
    assert "1.8k (1%)" in widget.render().plain

    # Message 2 (accumulated conversation)
    widget.set_context_usage(3500, 128000)
    assert "3.5k (3%)" in widget.render().plain

    # Message 3
    widget.set_context_usage(7200, 128000)
    assert "7.2k (6%)" in widget.render().plain

