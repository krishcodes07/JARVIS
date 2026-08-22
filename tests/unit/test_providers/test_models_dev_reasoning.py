"""Unit tests for models.dev reasoning capability lookups."""

from jarvis.providers.models_dev import (
    get_model_effort_values,
    get_model_info,
    get_model_reasoning_options,
    has_configurable_reasoning,
    is_only_thinking_model,
    is_reasoning_model,
)


def test_models_dev_configurable_reasoning_models():
    # OpenAI GPT-5.5 has effort options: none, low, medium, high, xhigh
    info = get_model_info("gpt-5.5")
    assert info is not None
    assert is_reasoning_model("gpt-5.5") is True
    assert has_configurable_reasoning("gpt-5.5") is True
    assert is_only_thinking_model("gpt-5.5") is False
    efforts = get_model_effort_values("gpt-5.5")
    assert "none" in efforts
    assert "high" in efforts

    # DeepSeek V4 Flash
    info_ds = get_model_info("deepseek/deepseek-v4-flash")
    assert info_ds is not None
    assert is_reasoning_model("deepseek/deepseek-v4-flash") is True
    assert has_configurable_reasoning("deepseek/deepseek-v4-flash") is True
    assert is_only_thinking_model("deepseek/deepseek-v4-flash") is False


def test_models_dev_only_thinking_models():
    # DeepSeek reasoner is only-thinking
    assert is_reasoning_model("deepseek-reasoner", "deepseek") is True
    assert has_configurable_reasoning("deepseek-reasoner", "deepseek") is False
    assert is_only_thinking_model("deepseek-reasoner", "deepseek") is True
    assert get_model_effort_values("deepseek-reasoner", "deepseek") == []


def test_models_dev_non_reasoning_models():
    assert is_reasoning_model("llama-3.3-70b-versatile", "groq") is False
    assert has_configurable_reasoning("llama-3.3-70b-versatile", "groq") is False
    assert is_only_thinking_model("llama-3.3-70b-versatile", "groq") is False
    assert get_model_effort_values("llama-3.3-70b-versatile", "groq") == []
