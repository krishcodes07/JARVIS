"""
Unit tests for JARVIS skills framework, list_skills tool, get_skill tool, skills config options, and engine prompt integration.
"""

from __future__ import annotations

import pytest

from jarvis.core.config import JarvisConfig, SkillsConfig
from jarvis.core.engine import JarvisEngine
from jarvis.core.exceptions import SkillNotFoundError
from jarvis.skills.manager import get_skill_readme, list_available_skills
from jarvis.tools.basic.get_skill import GetSkillTool
from jarvis.tools.basic.list_skills import ListSkillsTool


def test_list_available_skills():
    skills = list_available_skills()
    skill_names = [s["name"] for s in skills]

    assert len(skills) >= 5
    assert "deep-research" in skill_names
    assert "code-review" in skill_names
    assert "bug-hunting" in skill_names
    assert "system-architecture" in skill_names
    assert "data-analysis" in skill_names


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
async def test_list_skills_tool():
    tool = ListSkillsTool()
    output = await tool.execute()

    assert "Available JARVIS Skills:" in output
    assert "deep-research" in output
    assert "code-review" in output
    assert "bug-hunting" in output
    assert "system-architecture" in output
    assert "data-analysis" in output


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
    config = JarvisConfig.load()
    assert "list_skills" in config.tools.always_include
    assert "get_skill" in config.tools.always_include
    assert hasattr(config, "skills")
    assert config.skills.enabled is True


def test_skills_config_disable_all():
    config = JarvisConfig()
    config.skills.enabled = False

    skills = list_available_skills(config=config)
    assert skills == []

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

    assert "list_skills()" in summary
    assert "get_skill(skill_name=...)" in summary

    # When disabled
    engine.config.skills.enabled = False
    summary_disabled = engine._get_capability_summary([])
    assert "list_skills()" not in summary_disabled
