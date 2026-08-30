"""
Unit tests for ~/.jarvis user home directory architecture, path resolution, and .env key management.
"""

from __future__ import annotations

import os

from jarvis.core.config import (
    JarvisConfig,
    ensure_jarvis_home,
    get_jarvis_home,
    resolve_data_path,
    save_api_key_to_env,
)
from jarvis.skills.manager import get_skill_readme, list_available_skills


def test_get_jarvis_home(tmp_path, monkeypatch):
    custom_home = tmp_path / "custom_jarvis_home"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))

    home = get_jarvis_home()
    assert home == custom_home.resolve()


def test_ensure_jarvis_home(tmp_path, monkeypatch):
    custom_home = tmp_path / ".jarvis_test_env"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))

    home_dir = ensure_jarvis_home()
    assert home_dir == custom_home.resolve()

    # Check workspace subdirectories
    assert (custom_home / "config").exists()
    assert (custom_home / "workspace").exists()
    assert (custom_home / "workspace" / "sessions").exists()
    assert (custom_home / "workspace" / "long_term_memory").exists()
    assert (custom_home / "workspace" / "vector_store").exists()
    assert (custom_home / "workspace" / "knowledge_base").exists()
    assert (custom_home / "workspace" / "logs").exists()
    assert (custom_home / "workspace" / "cache").exists()
    assert (custom_home / "workspace" / "gui").exists()
    assert (custom_home / "workspace" / "skills").exists()

    # Check .env file initialized empty
    assert (custom_home / ".env").exists()

    # When JarvisConfig.load() is called without jarvis.yaml, defaults are used
    cfg = JarvisConfig.load()
    assert cfg.jarvis.name == "JARVIS"
    cfg.save()
    assert (custom_home / "config" / "jarvis.yaml").exists()


def test_resolve_data_path(tmp_path, monkeypatch):
    custom_home = tmp_path / ".jarvis_test_paths"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))

    path1 = resolve_data_path("workspace/sessions")
    assert path1 == custom_home / "workspace" / "sessions"

    path2 = resolve_data_path("data/vector_store")
    assert path2 == custom_home / "workspace" / "vector_store"

    # Absolute path remains unchanged
    abs_path = tmp_path / "absolute" / "path"
    assert resolve_data_path(abs_path) == abs_path


def test_custom_user_skill_discovery(tmp_path, monkeypatch):
    custom_home = tmp_path / ".jarvis_test_skills"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))
    ensure_jarvis_home()

    user_skill_dir = custom_home / "workspace" / "skills" / "user-custom-skill"
    user_skill_dir.mkdir(parents=True, exist_ok=True)
    (user_skill_dir / "README.md").write_text("# User Custom Skill\n> Custom user procedural skill test.", encoding="utf-8")

    skills = list_available_skills()
    skill_names = [s["name"] for s in skills]

    assert "user-custom-skill" in skill_names

    readme = get_skill_readme("user-custom-skill")
    assert "# User Custom Skill" in readme


def test_user_home_env_keys(tmp_path, monkeypatch):
    custom_home = tmp_path / ".jarvis_test_env_keys"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))

    ensure_jarvis_home()
    assert (custom_home / ".env").exists()

    save_api_key_to_env("TEST_JARVIS_API_KEY", "secret_key_12345")
    assert os.getenv("TEST_JARVIS_API_KEY") == "secret_key_12345"

    env_content = (custom_home / ".env").read_text(encoding="utf-8")
    assert "TEST_JARVIS_API_KEY=secret_key_12345" in env_content


def test_provider_base_urls_config(tmp_path, monkeypatch):
    custom_home = tmp_path / ".jarvis_test_base_urls"
    monkeypatch.setenv("JARVIS_HOME", str(custom_home))

    ensure_jarvis_home()
    cfg = JarvisConfig.load()
    assert cfg.provider.base_urls == {}

    cfg.provider.base_urls["ollama"] = "http://localhost:11434/v1"
    cfg.save()

    loaded = JarvisConfig.load()
    assert loaded.provider.base_urls.get("ollama") == "http://localhost:11434/v1"


