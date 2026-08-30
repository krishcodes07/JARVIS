"""
Unit Tests for JARVIS Reusable Core API Routes (jarvis.api).
"""

from __future__ import annotations

import contextlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from jarvis.api import create_api_app
from jarvis.api.deps import set_engine
from jarvis.core.config import JarvisConfig, MCPServerOverride


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine._initialized = True
    engine.last_used_model = "test-gpt-4o"
    engine.session = MagicMock()
    engine.session.session_id = "test-session-123"

    # Config mock
    engine.config = MagicMock()
    engine.config.jarvis.model_dump.return_value = {"name": "JARVIS"}
    engine.config.provider.model_dump.return_value = {"model": "gpt-4o", "active": "openai", "thinking": False, "reasoning_effort": "none"}
    engine.config.provider.model = "gpt-4o"
    engine.config.provider.active = "openai"
    engine.config.provider.thinking = False
    engine.config.provider.reasoning_effort = "none"
    engine.config.memory.model_dump.return_value = {}
    engine.config.tools.model_dump.return_value = {"auto_approve": False}
    engine.config.tools.auto_approve = False
    engine.config.voice.model_dump.return_value = {"enabled": True, "mode": "text"}
    engine.config.connectors.model_dump.return_value = {}
    engine.config.mcp.model_dump.return_value = {}

    # Tool registry mock
    engine.tool_registry = MagicMock()
    tool_mock = MagicMock()
    tool_mock.name = "test_tool"
    tool_mock.description = "A test tool"
    tool_mock.schema.category = "testing"
    tool_mock.schema.dangerous = False
    tool_mock.schema.parameters = []
    engine.tool_registry.list_tools.return_value = [tool_mock]

    # Connector manager mock
    engine.connector_manager = MagicMock()
    engine.connector_manager.get_statuses.return_value = []

    # Voice manager mock
    engine.voice_manager = MagicMock()
    engine.voice_manager.mode = "text"
    engine.voice_manager.config.enabled = True
    engine.voice_manager.config.tts.provider = "edge_tts"
    engine.voice_manager.config.tts.voice = "en-US-JennyNeural"
    engine.voice_manager.config.stt.provider = "whisper"

    # MCP manager mock
    engine.mcp_manager = MagicMock()
    engine.mcp_manager._manifests = {}
    engine.mcp_manager.registry.list_servers.return_value = []
    engine.mcp_manager.client.connections = {}

    # Provider manager mock
    engine.provider_manager = MagicMock()
    engine.provider_manager.switch_provider = AsyncMock()

    set_engine(engine)
    yield engine
    set_engine(None)


@pytest.fixture
def client(mock_engine):
    app = create_api_app(mock_engine)
    return TestClient(app)


def test_system_health(client):
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["engine_initialized"] is True
    assert data["active_model"] == "test-gpt-4o"


def test_system_health_reports_version_and_subsystems(client):
    """The About panel renders these, so the shape is part of the contract."""
    from jarvis import __version__

    data = client.get("/api/system/health").json()
    assert data["version"] == __version__

    subsystems = data["subsystems"]
    assert {"voice", "memory", "vector_memory", "tools", "mcp"} <= set(subsystems)
    # The fixture wires all of these onto the engine, so all report True.
    assert subsystems["tools"] is True
    assert subsystems["voice"] is True


def test_list_tools(client):
    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"


def test_get_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    cfg = response.json()
    assert "provider" in cfg
    assert cfg["provider"]["model"] == "gpt-4o"


def test_config_effort(client):
    response = client.get("/api/config/effort")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data

    post_res = client.post("/api/config/effort", json={"effort": "high"})
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"


def test_voice_status(client):
    response = client.get("/api/voice/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["mode"] == "text"


def test_mcp_servers_list(client):
    response = client.get("/api/mcp/servers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_connectors_list(client):
    response = client.get("/api/connectors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_skills_list(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_provider_connect_with_base_url(client, mock_engine):
    mock_engine.config.provider.base_urls = {}
    with patch("jarvis.core.config.save_api_key_to_env") as mock_save_env:
        response = client.post(
            "/api/config/provider/connect",
            json={
                "provider": "ollama",
                "api_key": "ollama-key",
                "base_url": "http://localhost:11434/v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["provider"] == "ollama"
        mock_save_env.assert_called_once()
        assert mock_engine.config.provider.base_urls["ollama"] == "http://localhost:11434/v1"
        mock_engine.config.save.assert_called_once()


def test_provider_connect_with_keys_dict(client, mock_engine):
    with patch("jarvis.core.config.save_api_key_to_env") as mock_save_env:
        response = client.post(
            "/api/config/provider/connect",
            json={
                "provider": "openai",
                "keys": {
                    "OPENAI_API_KEY": " sk-test123 ",
                    "EMPTY_KEY": "   ",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["provider"] == "openai"
        mock_save_env.assert_called_once_with("OPENAI_API_KEY", "sk-test123")



# ───────────────────────── Config deep-merge (PATCH) ─────────────────────────
#
# These use a real JarvisConfig rather than a MagicMock: the bug being guarded
# against was pydantic-specific — a shallow setattr loop replaced whole nested
# sections with raw dicts, and a MagicMock happily accepts that.


@pytest.fixture
def real_config_client(monkeypatch):
    """A TestClient whose engine holds a genuine JarvisConfig (save() stubbed)."""
    saves: list[int] = []
    monkeypatch.setattr(JarvisConfig, "save", lambda self, *a, **k: saves.append(1))

    cfg = JarvisConfig()
    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg

    set_engine(engine)
    yield TestClient(create_api_app(engine)), cfg, saves
    set_engine(None)


def test_config_patch_preserves_sibling_nested_sections(real_config_client):
    """Patching voice.stt must not clobber voice.tts."""
    client, cfg, _ = real_config_client
    assert cfg.voice.tts.provider == "edge_tts"

    response = client.patch("/api/config", json={"voice": {"stt": {"provider": "whisper"}}})
    assert response.status_code == 200
    assert response.json()["rejected"] == []

    assert cfg.voice.stt.provider == "whisper"
    # The sibling section survives, and as a model — not a raw dict.
    assert cfg.voice.tts.provider == "edge_tts"
    assert cfg.voice.tts.voice == "en-US-JennyNeural"
    assert not isinstance(cfg.voice.tts, dict)
    # Untouched leaves inside the patched section survive too.
    assert cfg.voice.stt.language == "en-US"
    assert cfg.voice.stt.sample_rate == 16000


def test_config_patch_writes_web_appearance(real_config_client):
    """The Appearance panel round-trip: theme choices must persist."""
    client, cfg, saves = real_config_client

    response = client.patch(
        "/api/config",
        json={"ui": {"web": {"theme": "matrix", "blob_style": "arc_reactor", "animations": False}}},
    )
    assert response.status_code == 200

    assert cfg.ui.web.theme == "matrix"
    assert cfg.ui.web.blob_style == "arc_reactor"
    assert cfg.ui.web.animations is False
    # Unrelated siblings in the same section are untouched.
    assert cfg.ui.web.port == 8000
    # And sibling sections of `ui` survive.
    assert cfg.ui.tui.theme == "dark"
    assert saves, "a patch must persist the config"


def test_config_patch_applies_previously_ignored_sections(real_config_client):
    """`connectors` was silently dropped by the old shallow update."""
    client, cfg, _ = real_config_client

    response = client.patch(
        "/api/config",
        json={"connectors": {"telegram": {"enabled": True, "allowed_users": ["@someone"]}}},
    )
    assert response.status_code == 200
    assert cfg.connectors.telegram.enabled is True
    assert cfg.connectors.telegram.allowed_users == ["@someone"]
    # Discord defaults untouched.
    assert cfg.connectors.discord.enabled is False


def test_config_patch_reports_unknown_keys_instead_of_failing(real_config_client):
    client, cfg, _ = real_config_client

    response = client.patch("/api/config", json={"voice": {"not_a_real_key": 1}})
    assert response.status_code == 200
    assert "voice.not_a_real_key" in response.json()["rejected"]


def test_config_patch_rejects_bad_leaf_type_without_corrupting(real_config_client):
    client, cfg, _ = real_config_client

    response = client.patch("/api/config", json={"ui": {"web": {"port": "not-a-port"}}})
    assert response.status_code == 200
    assert "ui.web.port" in response.json()["rejected"]
    assert cfg.ui.web.port == 8000


# ──────────────────────────── MCP server listing ────────────────────────────


def _mcp_client(servers):
    """TestClient over an engine whose config.mcp.servers is `servers`."""
    cfg = JarvisConfig()
    cfg.mcp.servers = servers

    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg
    engine.mcp_manager = MagicMock()
    engine.mcp_manager._manifests = {}
    engine.mcp_manager.registry.list_servers.return_value = []
    engine.mcp_manager.client.connections = {}

    set_engine(engine)
    return TestClient(create_api_app(engine)), cfg


def test_mcp_servers_list_with_typed_overrides():
    """`config.mcp.servers` holds MCPServerOverride models, not dicts.

    The old route used dict subscripting on those values and raised
    AttributeError, 500-ing the whole MCP settings panel.
    """
    client, _ = _mcp_client(
        {
            "filesystem": MCPServerOverride(
                enabled=True, transport="stdio", description="Local files"
            ),
            "github": MCPServerOverride(enabled=False),
        }
    )
    try:
        response = client.get("/api/mcp/servers")
        assert response.status_code == 200

        entries = {e["name"]: e for e in response.json()}
        assert entries["filesystem"]["enabled"] is True
        assert entries["filesystem"]["description"] == "Local files"
        assert entries["filesystem"]["transport"] == "stdio"
        # No manifest for these, so they read as user-added.
        assert entries["filesystem"]["custom"] is True
        assert entries["github"]["enabled"] is False
    finally:
        set_engine(None)


def test_mcp_servers_list_heals_legacy_dict_entries():
    """A hand-edited YAML can still hold raw dicts; normalise them in place.

    Healing matters because `cfg.save()` uses `model_dump()`, which cannot
    round-trip a raw dict sitting in a typed field.
    """
    client, cfg = _mcp_client({"legacy": {"enabled": True, "transport": "sse"}})
    try:
        response = client.get("/api/mcp/servers")
        assert response.status_code == 200

        entry = next(e for e in response.json() if e["name"] == "legacy")
        assert entry["enabled"] is True
        assert entry["transport"] == "sse"
        assert isinstance(cfg.mcp.servers["legacy"], MCPServerOverride)
    finally:
        set_engine(None)


def test_mcp_toggle_persists_enabled_flag_as_a_model():
    cfg = JarvisConfig()
    cfg.mcp.servers = {"filesystem": MCPServerOverride(enabled=True)}

    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg
    engine.mcp_manager = MagicMock()
    engine.mcp_manager.client.connections = {}
    engine.mcp_manager.client.disconnect = AsyncMock()
    engine.mcp_manager.disconnect_server = AsyncMock(return_value=(True, "disconnected"))

    set_engine(engine)
    try:
        with patch.object(JarvisConfig, "save", lambda self, *a, **k: None):
            client = TestClient(create_api_app(engine))
            response = client.post("/api/mcp/filesystem/toggle", json={"enabled": False})
            assert response.status_code == 200
            assert response.json()["connected"] is False

        override = cfg.mcp.servers["filesystem"]
        assert isinstance(override, MCPServerOverride)
        assert override.enabled is False
    finally:
        set_engine(None)


def test_mcp_toggle_creates_override_for_builtin_without_one():
    """Toggling a manifest-discovered built-in used to be a no-op.

    The old route only rewrote entries that already existed in
    ``config.mcp.servers``, so disabling a built-in never persisted.
    """
    cfg = JarvisConfig()
    cfg.mcp.servers = {}

    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg
    engine.mcp_manager = MagicMock()
    engine.mcp_manager.client.connections = {}
    engine.mcp_manager.disconnect_server = AsyncMock(return_value=(True, "not connected"))

    set_engine(engine)
    try:
        with patch.object(JarvisConfig, "save", lambda self, *a, **k: None):
            client = TestClient(create_api_app(engine))
            response = client.post("/api/mcp/memory/toggle", json={"enabled": False})
            assert response.status_code == 200
            assert response.json()["enabled"] is False

        assert cfg.mcp.servers["memory"].enabled is False
    finally:
        set_engine(None)


def test_mcp_servers_list_reports_live_connection_state():
    """`ServerConnection.connected` is the real attribute — not `is_connected`."""
    conn = MagicMock()
    conn.connected = True
    conn.tools = ["a", "b", "c"]

    cfg = JarvisConfig()
    cfg.mcp.servers = {"filesystem": MCPServerOverride(enabled=True)}

    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg
    engine.mcp_manager = MagicMock()
    engine.mcp_manager._manifests = {}
    engine.mcp_manager.registry.list_servers.return_value = []
    engine.mcp_manager.registry.get_all.return_value = {}
    engine.mcp_manager.client.connections = {"filesystem": conn}

    set_engine(engine)
    try:
        client = TestClient(create_api_app(engine))
        entry = next(
            e for e in client.get("/api/mcp/servers").json() if e["name"] == "filesystem"
        )
        assert entry["connected"] is True
        assert entry["tool_count"] == 3
    finally:
        set_engine(None)


def test_mcp_servers_list_falls_back_to_manifest_default():
    """A built-in with no override reads its enabled state from the manifest."""
    manifest = MagicMock()
    manifest.description = "Long-term memory"
    manifest.category = "core"
    manifest.oauth = None
    manifest.enabled_by_default = True

    cfg = JarvisConfig()
    cfg.mcp.servers = {}

    engine = MagicMock()
    engine._initialized = True
    engine.config = cfg
    engine.mcp_manager = MagicMock()
    engine.mcp_manager._manifests = {"memory": manifest}
    engine.mcp_manager.registry.list_servers.return_value = []
    engine.mcp_manager.registry.get_all.return_value = {}
    engine.mcp_manager.client.connections = {}

    set_engine(engine)
    try:
        client = TestClient(create_api_app(engine))
        entry = next(e for e in client.get("/api/mcp/servers").json() if e["name"] == "memory")
        assert entry["enabled"] is True
        assert entry["connected"] is False
        assert entry["custom"] is False
    finally:
        set_engine(None)


# ─────────────────────── Session rename (non-destructive) ───────────────────────


@pytest.fixture
def sessions_dir(tmp_path):
    """Point the sessions routes at an isolated directory."""
    d = tmp_path / "sessions"
    d.mkdir()
    with patch("jarvis.api.routes.sessions.get_sessions_dir", return_value=d):
        yield d


MESSAGES = [
    {
        "role": "user",
        "content": "What is the airspeed velocity of an unladen swallow?",
        "timestamp": "2026-01-01T00:00:00+00:00",
    },
    {"role": "assistant", "content": "African or European?"},
]


def test_rename_session_preserves_message_content(client, sessions_dir):
    """Renaming must touch the title sidecar only, never the transcript.

    The previous implementation overwrote the first user message with the new
    title, silently destroying conversation history.
    """
    sid = "sess-abc123"
    session_file = sessions_dir / f"{sid}.json"
    session_file.write_text(json.dumps(MESSAGES), encoding="utf-8")

    response = client.post(f"/api/sessions/{sid}/rename", json={"title": "Swallow physics"})
    assert response.status_code == 200
    assert response.json()["title"] == "Swallow physics"

    # Transcript identical.
    assert json.loads(session_file.read_text(encoding="utf-8")) == MESSAGES

    # ...while the listing reflects the new title.
    listed = client.get("/api/sessions").json()
    entry = next(s for s in listed if s["session_id"] == sid)
    assert entry["title"] == "Swallow physics"
    assert entry["message_count"] == 2


def test_list_sessions_derives_title_when_not_renamed(client, sessions_dir):
    sid = "sess-derived"
    (sessions_dir / f"{sid}.json").write_text(json.dumps(MESSAGES), encoding="utf-8")

    entry = next(s for s in client.get("/api/sessions").json() if s["session_id"] == sid)
    assert entry["title"].startswith("What is the airspeed velocity")


def test_titles_sidecar_is_not_listed_as_a_session(client, sessions_dir):
    sid = "sess-xyz"
    (sessions_dir / f"{sid}.json").write_text(json.dumps(MESSAGES), encoding="utf-8")
    client.post(f"/api/sessions/{sid}/rename", json={"title": "Renamed"})

    assert (sessions_dir / "_titles.json").exists()
    ids = [s["session_id"] for s in client.get("/api/sessions").json()]
    assert ids == [sid]


def test_rename_unknown_session_is_404(client, sessions_dir):
    response = client.post("/api/sessions/nope/rename", json={"title": "x"})
    assert response.status_code == 404


def test_delete_session_prunes_its_title(client, sessions_dir):
    sid = "sess-doomed"
    (sessions_dir / f"{sid}.json").write_text(json.dumps(MESSAGES), encoding="utf-8")
    client.post(f"/api/sessions/{sid}/rename", json={"title": "Temporary"})

    assert client.delete(f"/api/sessions/{sid}").status_code == 200

    titles = json.loads((sessions_dir / "_titles.json").read_text(encoding="utf-8"))
    assert sid not in titles, "a recycled session id must not inherit an old title"



# ─── Voice: provider-scoped voice catalogue ────────────────────────
# The settings panel switches the TTS dropdown and expects that provider's voices
# immediately — before the change is saved, and even while voice is disabled.


def _voice(vid, name, gender="", locale=""):
    v = MagicMock()
    v.id = vid
    v.name = name
    v.gender = gender
    v.locale = locale
    return v


def test_voice_voices_uses_requested_provider(client):
    seen: dict[str, object] = {}

    async def fake_list(provider, tts_config=None, use_cache=True):
        seen["provider"] = provider
        return [_voice("21m00", "Rachel", "female")]

    with patch("jarvis.api.routes.voice.list_voices_for_provider", new=fake_list):
        response = client.get("/api/voice/voices", params={"provider": "elevenlabs"})

    assert response.status_code == 200
    assert seen["provider"] == "elevenlabs"
    assert response.json() == [
        {"id": "21m00", "name": "Rachel", "gender": "female", "locale": ""}
    ]


def test_voice_voices_falls_back_to_the_configured_provider(client, mock_engine):
    mock_engine.config.voice.tts.provider = "edge_tts"
    seen: dict[str, object] = {}

    async def fake_list(provider, tts_config=None, use_cache=True):
        seen["provider"] = provider
        return []

    with patch("jarvis.api.routes.voice.list_voices_for_provider", new=fake_list):
        assert client.get("/api/voice/voices").status_code == 200

    assert seen["provider"] == "edge_tts"


def test_voice_voices_surfaces_a_missing_key_as_400(client):
    from jarvis.core.exceptions import VoiceAuthError

    async def fake_list(provider, tts_config=None, use_cache=True):
        raise VoiceAuthError("ELEVENLABS_API_KEY is not set")

    with patch("jarvis.api.routes.voice.list_voices_for_provider", new=fake_list):
        response = client.get("/api/voice/voices", params={"provider": "elevenlabs"})

    # An actionable message beats an empty dropdown.
    assert response.status_code == 400
    assert "ELEVENLABS_API_KEY" in response.json()["detail"]


def test_voice_providers_flags_the_active_one(client, mock_engine):
    mock_engine.config.voice.tts.provider = "elevenlabs"
    response = client.get("/api/voice/providers")
    assert response.status_code == 200
    active = [p["id"] for p in response.json() if p["active"]]
    assert active == ["elevenlabs"]


def test_voice_mode_persists_without_a_live_manager(client, mock_engine):
    mock_engine.voice_manager = None
    response = client.post("/api/voice/mode", json={"mode": "voice"})
    assert response.status_code == 200
    assert response.json()["mode"] == "voice"
    # The choice has to stick so it applies the next time voice comes up.
    assert mock_engine.config.voice.mode == "voice"
    mock_engine.config.save.assert_called()


def test_voice_mode_rejects_an_unknown_mode(client):
    assert client.post("/api/voice/mode", json={"mode": "sing"}).status_code == 400


# ─── Config PATCH rebuilds the voice subsystem ─────────────────────


@pytest.fixture
def voice_reload_client(monkeypatch):
    """A client whose engine records calls to the voice-reload hook."""
    monkeypatch.setattr(JarvisConfig, "save", lambda self, *a, **k: None)

    engine = MagicMock()
    engine._initialized = True
    engine.config = JarvisConfig()
    engine.reload_voice = AsyncMock(return_value=True)

    set_engine(engine)
    yield TestClient(create_api_app(engine)), engine
    set_engine(None)


def test_config_patch_reloads_voice(voice_reload_client):
    client, engine = voice_reload_client

    response = client.patch("/api/config", json={"voice": {"enabled": True}})

    # Otherwise a provider swap only takes effect after a restart.
    assert response.status_code == 200
    assert response.json()["voice_reloaded"] is True
    engine.reload_voice.assert_awaited_once()


def test_config_patch_without_voice_does_not_reload(voice_reload_client):
    client, engine = voice_reload_client

    response = client.patch("/api/config", json={"tools": {"auto_approve": False}})

    assert response.status_code == 200
    assert response.json()["voice_reloaded"] is None
    engine.reload_voice.assert_not_awaited()


def test_config_patch_survives_a_failing_voice_reload(voice_reload_client):
    client, engine = voice_reload_client
    engine.reload_voice = AsyncMock(side_effect=RuntimeError("no elevenlabs key"))

    response = client.patch("/api/config", json={"voice": {"tts": {"provider": "elevenlabs"}}})

    # The setting is still saved; only the live rebuild failed.
    assert response.status_code == 200
    assert response.json()["voice_reloaded"] is False


# ─── Skills: create, read, delete ──────────────────────────────────


@pytest.fixture
def skills_client(client, tmp_path, monkeypatch):
    """A client whose user skills directory is a throwaway folder."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / ".jarvis_api_skills"))
    from jarvis.core.config import ensure_jarvis_home

    ensure_jarvis_home()
    return client


SKILL_MD = "# Api Made Skill\n\n> Created through the settings panel.\n\n## Steps\n1. Do it.\n"


def test_skills_create_read_and_delete(skills_client):
    created = skills_client.post("/api/skills", json={"content": SKILL_MD})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "api-made-skill"
    assert body["custom"] is True

    listed = skills_client.get("/api/skills").json()
    entry = next(s for s in listed if s["name"] == "api-made-skill")
    assert entry["enabled"] is True
    assert entry["custom"] is True

    detail = skills_client.get("/api/skills/api-made-skill")
    assert detail.status_code == 200
    assert "## Steps" in detail.json()["content"]

    removed = skills_client.delete("/api/skills/api-made-skill")
    assert removed.status_code == 200
    assert removed.json() == {"status": "deleted", "name": "api-made-skill"}
    assert all(s["name"] != "api-made-skill" for s in skills_client.get("/api/skills").json())


def test_skills_create_collision_is_400_until_overwrite(skills_client):
    assert skills_client.post("/api/skills", json={"content": SKILL_MD}).status_code == 201

    clash = skills_client.post("/api/skills", json={"content": SKILL_MD})
    assert clash.status_code == 400
    assert "already exists" in clash.json()["detail"]

    forced = skills_client.post(
        "/api/skills",
        json={"content": "# Api Made Skill\n\n> Second take.\n", "overwrite": True},
    )
    assert forced.status_code == 201
    assert forced.json()["description"] == "Second take."


def test_skills_create_rejects_empty_content(skills_client):
    # min_length=1 on the model, so this never reaches the manager.
    assert skills_client.post("/api/skills", json={"content": ""}).status_code == 422


def test_skills_delete_builtin_is_400(skills_client):
    response = skills_client.delete("/api/skills/coding")
    assert response.status_code == 400
    assert "built in" in response.json()["detail"]


def test_skills_directory_endpoint_is_not_shadowed_by_the_name_route(skills_client):
    response = skills_client.get("/api/skills/directory")
    assert response.status_code == 200
    assert response.json()["path"].endswith("skills")
