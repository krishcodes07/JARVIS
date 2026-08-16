"""
Unit tests for JARVIS skills framework, format_skills_for_prompt, get_skill tool, skills config options, and engine prompt integration.
"""

from __future__ import annotations

import pytest

from jarvis.core.config import JarvisConfig, SkillsConfig
from jarvis.core.engine import JarvisEngine
from jarvis.core.exceptions import SkillNotFoundError
from jarvis.skills.manager import format_skills_for_prompt, get_skill_readme, list_available_skills
from jarvis.tools.basic.get_skill import GetSkillTool


def test_list_available_skills():
    skills = list_available_skills()
    skill_names = [s["name"] for s in skills]

    assert len(skills) >= 5
    assert "deep-research" in skill_names
    assert "code-review" in skill_names
    assert "bug-hunting" in skill_names
    assert "system-architecture" in skill_names
    assert "data-analysis" in skill_names
    assert "coding" in skill_names

    for s in skills:
        assert s["description"] and s["description"] != "No description provided."


def test_format_skills_for_prompt():
    prompt_text = format_skills_for_prompt()
    assert "Available Skills (Procedural Workflows)" in prompt_text
    assert "`deep-research`:" in prompt_text
    assert "`coding`:" in prompt_text
    assert "`bug-hunting`:" in prompt_text
    assert "get_skill(skill_name=...)" in prompt_text


def test_get_skill_readme():
    readme = get_skill_readme("deep-research")
    assert "# Deep Research Skill" in readme
    assert "Step-by-Step Execution Protocol" in readme

    # Case insensitive and underscore alias support
    readme_code = get_skill_readme("code_review")
    assert "# Code Review Skill" in readme_code


def test_get_skill_readme_not_found():
    with pytest.raises(SkillNotFoundError):
        get_skill_readme("non-existent-skill")


@pytest.mark.asyncio
async def test_get_skill_tool():
    tool = GetSkillTool()

    # Valid skill
    output = await tool.execute(skill_name="deep-research")
    assert "# Deep Research Skill" in output

    # Invalid skill
    error_output = await tool.execute(skill_name="unknown-skill")
    assert "Error:" in error_output


def test_config_always_include_skills():
    config = JarvisConfig()
    assert "get_skill" in config.tools.always_include
    assert "list_skills" not in config.tools.always_include
    assert hasattr(config, "skills")
    assert config.skills.enabled is True


def test_skills_config_disable_all():
    config = JarvisConfig()
    config.skills.enabled = False

    skills = list_available_skills(config=config)
    assert skills == []

    prompt_text = format_skills_for_prompt(config=config)
    assert prompt_text == ""

    with pytest.raises(SkillNotFoundError):
        get_skill_readme("deep-research", config=config)


def test_skills_config_disable_particular_skill():
    config = JarvisConfig()
    config.skills.disabled_skills = ["code-review", "bug-hunting"]

    skills = list_available_skills(config=config)
    skill_names = [s["name"] for s in skills]

    assert "deep-research" in skill_names
    assert "code-review" not in skill_names
    assert "bug-hunting" not in skill_names

    prompt_text = format_skills_for_prompt(config=config)
    assert "`deep-research`:" in prompt_text
    assert "`code-review`:" not in prompt_text

    # Allowed skill works
    readme = get_skill_readme("deep-research", config=config)
    assert "# Deep Research Skill" in readme

    # Disabled skill raises SkillNotFoundError
    with pytest.raises(SkillNotFoundError) as exc_info:
        get_skill_readme("code-review", config=config)
    assert "currently disabled" in str(exc_info.value)


def test_engine_capability_summary():
    engine = JarvisEngine()
    engine.config = JarvisConfig()
    summary = engine._get_capability_summary([])

    assert "Available Skills (Procedural Workflows)" in summary
    assert "`deep-research`:" in summary
    assert "`coding`:" in summary
    assert "get_skill(skill_name=...)" in summary
    assert "list_skills()" not in summary

    # When disabled
    engine.config.skills.enabled = False
    summary_disabled = engine._get_capability_summary([])
    assert "Available Skills (Procedural Workflows):" not in summary_disabled
    assert "`deep-research`:" not in summary_disabled
