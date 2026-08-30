"""
Unit tests for user-created skills: creation from pasted README content, deletion,
and the ``include_disabled`` paths the settings UI depends on.
"""

from __future__ import annotations

import pytest

from jarvis.core.config import JarvisConfig, ensure_jarvis_home
from jarvis.core.exceptions import SkillLoadError, SkillNotFoundError
from jarvis.skills.manager import (
    create_skill,
    delete_skill,
    derive_skill_name,
    get_skill_readme,
    get_user_skills_directory,
    list_available_skills,
    slugify_skill_name,
)

README = """# Release Checklist

> Ship a JARVIS release without breaking anything.

## Steps
1. Run the test suite.
2. Tag the commit.
"""


@pytest.fixture
def jarvis_home(tmp_path, monkeypatch):
    """Point ~/.jarvis at a throwaway directory for the whole test."""
    home = tmp_path / ".jarvis_skills_home"
    monkeypatch.setenv("JARVIS_HOME", str(home))
    ensure_jarvis_home()
    return home


def _find(skills: list[dict], name: str) -> dict | None:
    return next((s for s in skills if s["name"] == name), None)


# ─── Naming ────────────────────────────────────────────────────────


def test_slugify_strips_path_separators_and_traversal():
    assert slugify_skill_name("../../etc/passwd") == "etc-passwd"
    assert slugify_skill_name("  My Skill!  ") == "my-skill"
    assert slugify_skill_name("///") == ""
    assert len(slugify_skill_name("x" * 200)) == 64


def test_derive_name_prefers_front_matter_then_heading():
    assert derive_skill_name('---\nname: "Deep Research"\n---\n# Other\n') == "deep-research"
    assert derive_skill_name("# Release Checklist\n\nbody") == "release-checklist"
    # Last resort: the first six words of the first non-empty line.
    assert derive_skill_name("just some prose about a thing here") == "just-some-prose-about-a-thing"
    assert derive_skill_name("   ") == ""


# ─── Creation ──────────────────────────────────────────────────────


def test_create_skill_writes_readme_and_is_discoverable(jarvis_home):
    created = create_skill(README)

    assert created["name"] == "release-checklist"
    assert created["description"] == "Ship a JARVIS release without breaking anything."

    readme = get_user_skills_directory() / "release-checklist" / "README.md"
    assert readme.exists()
    assert readme.read_text(encoding="utf-8").startswith("# Release Checklist")

    entry = _find(list_available_skills(), "release-checklist")
    assert entry is not None
    assert entry["enabled"] is True
    # Written under the user root, so the UI may offer to delete it.
    assert entry["custom"] is True

    assert "## Steps" in get_skill_readme("release-checklist")


def test_create_skill_honours_an_explicit_name(jarvis_home):
    created = create_skill(README, name="My Ship Guide")
    assert created["name"] == "my-ship-guide"
    assert (get_user_skills_directory() / "my-ship-guide" / "README.md").exists()


def test_create_skill_rejects_empty_content(jarvis_home):
    with pytest.raises(SkillLoadError):
        create_skill("   \n  ")


def test_create_skill_rejects_unnameable_content(jarvis_home):
    with pytest.raises(SkillLoadError):
        create_skill("!!! ???")


def test_create_skill_refuses_collision_then_overwrites_on_request(jarvis_home):
    create_skill(README)

    with pytest.raises(SkillLoadError, match="already exists"):
        create_skill(README)

    replacement = "# Release Checklist\n\n> Replaced body.\n"
    created = create_skill(replacement, overwrite=True)
    assert created["description"] == "Replaced body."
    assert "Replaced body." in get_skill_readme("release-checklist")


def test_create_skill_clears_a_stale_disabled_entry(jarvis_home):
    cfg = JarvisConfig.load()
    cfg.skills.disabled_skills = ["release_checklist", "coding"]

    create_skill(README, config=cfg)

    # The new skill must be usable immediately; unrelated entries stay put.
    assert cfg.skills.disabled_skills == ["coding"]
    entry = _find(list_available_skills(config=cfg), "release-checklist")
    assert entry is not None and entry["enabled"] is True


def test_create_skill_cannot_escape_the_user_directory(jarvis_home):
    created = create_skill(README, name="../../evil")
    assert created["name"] == "evil"
    assert (get_user_skills_directory() / "evil").is_dir()


# ─── Deletion ──────────────────────────────────────────────────────


def test_delete_skill_removes_the_folder(jarvis_home):
    create_skill(README)
    assert delete_skill("release-checklist") == "release-checklist"
    assert not (get_user_skills_directory() / "release-checklist").exists()
    assert _find(list_available_skills(), "release-checklist") is None


def test_delete_unknown_skill_raises_not_found(jarvis_home):
    with pytest.raises(SkillNotFoundError):
        delete_skill("no-such-skill")


def test_delete_refuses_packaged_builtins(jarvis_home):
    # 'coding' ships inside src/jarvis/skills, so an update must not be undoable
    # from the settings panel.
    with pytest.raises(SkillLoadError, match="built in"):
        delete_skill("coding")


# ─── Disabled skills stay visible to the UI ────────────────────────


def test_disabled_skill_is_listed_when_include_disabled(jarvis_home):
    create_skill(README)
    cfg = JarvisConfig.load()
    cfg.skills.disabled_skills = ["release-checklist"]

    assert _find(list_available_skills(config=cfg), "release-checklist") is None

    entry = _find(list_available_skills(config=cfg, include_disabled=True), "release-checklist")
    assert entry is not None
    # Listed but flagged off — otherwise the toggle would be one-way.
    assert entry["enabled"] is False

    with pytest.raises(SkillNotFoundError):
        get_skill_readme("release-checklist", config=cfg)
    assert "## Steps" in get_skill_readme("release-checklist", config=cfg, include_disabled=True)


def test_master_switch_off_still_lists_for_the_panel(jarvis_home):
    create_skill(README)
    cfg = JarvisConfig.load()
    cfg.skills.enabled = False

    assert list_available_skills(config=cfg) == []

    listed = list_available_skills(config=cfg, include_disabled=True)
    entry = _find(listed, "release-checklist")
    assert entry is not None
    assert entry["enabled"] is False
