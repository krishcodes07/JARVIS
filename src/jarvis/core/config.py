"""
JARVIS Configuration — Loads and manages all configuration.

Configuration sources (in priority order):
1. Environment variables (~/.jarvis/.env and system env)
2. YAML config file (~/.jarvis/config/jarvis.yaml or config/jarvis.yaml)
3. JSON config files (providers.json, models.json)
4. Default values
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ─── Project Root & User Home Detection ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/jarvis/core -> project root


def get_jarvis_home() -> Path:
    """Get the JARVIS user home directory path (~/.jarvis)."""
    env_home = os.getenv("JARVIS_HOME")
    if env_home:
        return Path(env_home).resolve()
    return (Path.home() / ".jarvis").resolve()


JARVIS_HOME = get_jarvis_home()
JARVIS_CONFIG_DIR = JARVIS_HOME / "config"
JARVIS_WORKSPACE_DIR = JARVIS_HOME / "workspace"

# Backward compatibility aliases
CONFIG_DIR = JARVIS_CONFIG_DIR
DATA_DIR = JARVIS_WORKSPACE_DIR


def ensure_jarvis_home() -> Path:
    """Ensure ~/.jarvis home directory structure exists and copy template configs/.env if missing."""
    home_dir = get_jarvis_home()
    config_dir = home_dir / "config"
    workspace_dir = home_dir / "workspace"

    # Create workspace subdirectories
    subdirs = [
        config_dir,
        workspace_dir,
        workspace_dir / "sessions",
        workspace_dir / "long_term_memory",
        workspace_dir / "vector_store",
        workspace_dir / "knowledge_base",
        workspace_dir / "logs",
        workspace_dir / "cache",
        workspace_dir / "gui",
        workspace_dir / "skills",
        workspace_dir / "automation_logs",
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)

    # Copy template config files from PROJECT_ROOT/config if missing in user home
    repo_config_dir = PROJECT_ROOT / "config"
    for item in ["jarvis.yaml", "providers.json", "models.json"]:
        dst_file = config_dir / item
        if not dst_file.exists():
            src_file = repo_config_dir / item
            if repo_config_dir.exists() and src_file.exists():
                try:
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"Initialized default config file {dst_file} from repository template.")
                except Exception as e:
                    logger.warning(f"Failed to copy config template {src_file} to {dst_file}: {e}")
            elif item == "jarvis.yaml":
                try:
                    JarvisConfig().save(dst_file)
                except Exception as e:
                    logger.warning(f"Failed to create default config file {dst_file}: {e}")

    # Copy .env template to ~/.jarvis/.env if missing
    user_env_file = home_dir / ".env"
    if not user_env_file.exists():
        repo_env = PROJECT_ROOT / ".env"
        repo_env_example = PROJECT_ROOT / ".env.example"
        src_env = repo_env if repo_env.exists() else (repo_env_example if repo_env_example.exists() else None)
        if src_env:
            try:
                shutil.copy2(src_env, user_env_file)
                logger.info(f"Initialized user environment file {user_env_file} from {src_env.name}.")
            except Exception as e:
                logger.warning(f"Failed to copy env template to {user_env_file}: {e}")

    # Copy models_dev_cache.json from PROJECT_ROOT/data if missing in user workspace
    repo_cache_file = PROJECT_ROOT / "data" / "models_dev_cache.json"
    user_cache_file = workspace_dir / "models_dev_cache.json"
    if repo_cache_file.exists() and not user_cache_file.exists():
        try:
            shutil.copy2(repo_cache_file, user_cache_file)
            logger.info(f"Initialized models_dev_cache.json in {user_cache_file} from repository data.")
        except Exception as e:
            logger.warning(f"Failed to copy models_dev_cache.json template to {user_cache_file}: {e}")

    # Sync legacy sessions if present
    from jarvis.core.paths import sync_legacy_sessions
    sync_legacy_sessions()

    return home_dir


def resolve_data_path(path_input: str | Path) -> Path:
    """Resolve a data or storage path relative to ~/.jarvis/workspace."""
    from jarvis.core.paths import resolve_data_path as _resolve_data_path
    return _resolve_data_path(path_input)


# ═══════════════════════════════════════════════════════════════
# Configuration Models (Pydantic)
# ═══════════════════════════════════════════════════════════════


class FallbackConfig(BaseModel):
    """Fallback provider configuration."""
    enabled: bool = True
    provider: str = "openrouter"
    model: str = "anthropic/claude-sonnet-4"


class ProviderConfig(BaseModel):
    """LLM provider settings."""
    active: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    thinking: bool = True
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)


class ConversationMemoryConfig(BaseModel):
    """Conversation (short-term) memory settings."""
    enabled: bool = True
    backend: str = "json"
    max_messages: int = 100
    auto_summarize: bool = True
    summarize_after: int = 50


class LongTermMemoryConfig(BaseModel):
    """Long-term memory settings."""
    enabled: bool = True
    auto_extract: bool = True
    provider: str = ""          # Provider used for extraction ("" = active provider)
    model: str = ""             # Model used for extraction ("" = active model)
    storage_path: str = "workspace/long_term_memory"


class VectorMemoryConfig(BaseModel):
    """Vector / semantic memory settings."""
    enabled: bool = True
    backend: str = "chromadb"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 512
    chunk_overlap: int = 50
    collection_name: str = "jarvis_memory"
    storage_path: str = "workspace/vector_store"
    knowledge_base_path: str = "workspace/knowledge_base"


class MemoryConfig(BaseModel):
    """Memory subsystem settings."""
    conversation: ConversationMemoryConfig = Field(default_factory=ConversationMemoryConfig)
    long_term: LongTermMemoryConfig = Field(default_factory=LongTermMemoryConfig)
    vector: VectorMemoryConfig = Field(default_factory=VectorMemoryConfig)


class SandboxConfig(BaseModel):
    """Sandbox settings for dangerous tool execution."""
    enabled: bool = True
    workspace: str = "."                    # Base directory for filesystem tools
    extra_paths: list[str] = Field(default_factory=list)  # Additional allowed roots
    blocked_commands: list[str] = Field(default_factory=list)  # Extra blocked command patterns


class ToolsConfig(BaseModel):
    """Tool system settings."""
    enabled: bool = True
    auto_approve: bool = False
    max_turns: int = 25
    timeout: int = 30
    max_retries: int = 2
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    always_include: list[str] = Field(
        default_factory=lambda: [
            "list_tools",
            "get_schema",
            "list_directory",
            "read_file",
            "write_file",
            "edit_file",
            "append_file",
            "make_directory",
            "delete_file",
            "web_search",
            "read_url",
            "get_skill",
        ]
    )
    categories: dict[str, bool] = Field(
        default_factory=lambda: {
            "basic": True,
            "filesystem": True,
            "system": True,
            "code": True,
            "desktop": True,
        }
    )


class SkillsConfig(BaseModel):
    """Skills subsystem settings."""
    enabled: bool = True
    skills_dir: str = "src/jarvis/skills"
    disabled_skills: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    """MCP subsystem settings."""
    enabled: bool = True
    auto_start: list[str] = Field(default_factory=list)
    timeout: int = 90
    servers_config: str = "src/jarvis/mcp/servers.json"
    servers: dict[str, Any] = Field(default_factory=dict)


class TTSConfig(BaseModel):
    """Text-to-speech provider settings."""
    provider: str = "edge_tts"                 # edge_tts | elevenlabs
    voice: str = "en-US-JennyNeural"           # voice name / id (per provider)
    model: str = ""                            # provider model id (e.g. elevenlabs)
    rate: str = "+0%"                          # edge_tts speech rate
    volume: str = "+0%"                        # edge_tts volume
    pitch: str = "+0Hz"                        # edge_tts pitch
    stream: bool = True                        # use streaming TTS when supported
    output_format: str = "mp3_44100_128"       # elevenlabs audio format


class STTConfig(BaseModel):
    """Speech-to-text provider settings."""
    provider: str = "sr"                       # sr | whisper
    engine: str = "google"                     # sr recognizer: google | whisper | sphinx | vosk
    model: str = "base"                        # whisper model size (tiny..large)
    language: str = "en-US"                    # recognition language
    device: str = "auto"                       # faster-whisper device (auto | cpu | cuda)
    compute_type: str = "default"              # faster-whisper compute type
    download_root: str = ""                    # faster-whisper model cache dir
    energy_threshold: float = 300.0            # VAD energy threshold (int16 scale)
    pause_threshold: float = 0.8               # silence (s) that ends an utterance
    max_duration: float = 30.0                 # max recording length (s)
    sample_rate: int = 16000                   # recording sample rate (Hz)


class AudioConfig(BaseModel):
    """Audio hardware device settings."""
    input_device: int | str | None = None
    output_device: int | str | None = None
    sample_rate: int = 44100


class VoiceConfig(BaseModel):
    """Voice subsystem settings."""
    enabled: bool = False
    mode: str = "text"                         # text | voice | push_to_talk
    auto_send_msg: bool = True                 # automatically send STT text as message
    tts: TTSConfig = Field(default_factory=TTSConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)

    @field_validator("auto_send_msg", mode="before")
    @classmethod
    def parse_auto_send_msg(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("true", "1", "yes", "on"):
                return True
            if clean in ("false", "0", "no", "off", "false"):
                return False
        return True


class TUIConfig(BaseModel):
    """TUI display settings."""
    theme: str = "dark"
    show_tool_output: bool = True
    show_thinking: bool = False


class WebConfig(BaseModel):
    """Web UI settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    theme: str = "dark"


class GUIConfig(BaseModel):
    """GUI settings."""
    theme: str = "dark"
    window_size: str = "1200x800"
    opacity: float = 0.95


class UIConfig(BaseModel):
    """UI settings."""
    default: str = "tui"
    tui: TUIConfig = Field(default_factory=TUIConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    gui: GUIConfig = Field(default_factory=GUIConfig)


class TelegramConnectorConfig(BaseModel):
    """Telegram bot connector settings."""
    enabled: bool = False
    bot_token: str = ""                         # Can also be loaded from TELEGRAM_BOT_TOKEN env var
    allowed_users: list[str | int] = Field(default_factory=list)  # Allowed user IDs or usernames (empty = allow all)
    polling_timeout: int = 30                  # Long polling timeout in seconds
    send_typing: bool = True                   # Send typing action while generating responses
    max_message_length: int = 4000             # Telegram message character limit (max 4096)


class DiscordConnectorConfig(BaseModel):
    """Discord bot connector settings."""
    enabled: bool = False
    bot_token: str = ""                         # Can also be loaded from DISCORD_BOT_TOKEN env var
    allowed_channels: list[str | int] = Field(default_factory=list)
    allowed_users: list[str | int] = Field(default_factory=list)
    allowed_guilds: list[str | int] = Field(default_factory=list)
    send_typing: bool = True
    max_message_length: int = 2000


class AutomationConfig(BaseModel):
    """Full PC Control and Desktop Automation settings."""
    enabled: bool = True
    grounding_mode: str = "uia"                     # uia | vision | hybrid
    max_steps: int = 30                             # Maximum autonomous execution steps per goal
    step_delay: float = 0.5                         # Delay in seconds between actions
    emergency_hotkey: str = "ctrl+alt+q"            # Global emergency abort key sequence
    failsafe: bool = True                           # PyAutoGUI mouse corner failsafe
    human_mouse_speed: bool = True                  # Smooth human-like mouse glide
    mouse_speed_seconds: float = 0.3                # Average glide duration for mouse movements
    screenshot_downscale: float = 1.0               # Scale factor for screenshot capture
    protected_apps: list[str] = Field(
        default_factory=lambda: [
            "1password",
            "bitwarden",
            "keepass",
            "lastpass",
            "authenticator",
            "windows security",
        ]
    )
    require_confirmation_for_sensitive: bool = True # Gate destructive actions
    log_screenshots: bool = True                    # Save step screenshots in workspace/automation_logs


class ConnectorsConfig(BaseModel):
    """External messaging connectors settings."""
    enabled: bool = True                        # Master switch for connectors subsystem
    telegram: TelegramConnectorConfig = Field(default_factory=TelegramConnectorConfig)
    discord: DiscordConnectorConfig = Field(default_factory=DiscordConnectorConfig)


class JarvisMetaConfig(BaseModel):
    """Top-level JARVIS metadata."""
    name: str = "JARVIS"
    version: str = "0.1.0"
    persona: str = "professional_assistant"
    log_level: str = "INFO"


class JarvisConfig(BaseModel):
    """Complete JARVIS configuration.

    This is the root configuration model that aggregates all subsystem configs.
    """
    jarvis: JarvisMetaConfig = Field(default_factory=JarvisMetaConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> JarvisConfig:
        """Load configuration from YAML file and environment.

        Args:
            config_path: Path to jarvis.yaml. If None, uses ~/.jarvis/config/jarvis.yaml (or repo fallback).

        Returns:
            Fully loaded JarvisConfig instance.
        """
        # Ensure ~/.jarvis home directory structure & .env file exist
        ensure_jarvis_home()

        # Load environment variables (.env) from repo root and user home (~/.jarvis/.env overrides repo)
        repo_env_path = PROJECT_ROOT / ".env"
        home_env_path = get_jarvis_home() / ".env"

        if repo_env_path.exists():
            load_dotenv(repo_env_path)
            logger.info(f"Loaded environment from {repo_env_path}")
        if home_env_path.exists():
            load_dotenv(home_env_path, override=True)
            logger.info(f"Loaded environment from {home_env_path}")

        # Determine YAML config path
        if config_path is None:
            user_config_path = get_jarvis_home() / "config" / "jarvis.yaml"
            repo_config_path = PROJECT_ROOT / "config" / "jarvis.yaml"
            if user_config_path.exists():
                config_path = user_config_path
            elif repo_config_path.exists():
                config_path = repo_config_path
            else:
                config_path = user_config_path

        if config_path and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {config_path}")
        else:
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            raw_config = {}

        return cls.model_validate(raw_config)

    def save(self, config_path: Path | None = None) -> None:
        """Save current configuration to YAML file.

        Args:
            config_path: Path to save to. If None, uses ~/.jarvis/config/jarvis.yaml.
        """
        if config_path is None:
            config_path = get_jarvis_home() / "config" / "jarvis.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        logger.info(f"Config saved to {config_path}")

    def get_api_key(self, env_var: str) -> str | None:
        """Get an API key from environment variables."""
        return os.getenv(env_var)

    def load_providers(self) -> list[dict[str, Any]]:
        """Load provider definitions from providers.json."""
        providers_path = get_jarvis_home() / "config" / "providers.json"
        if not providers_path.exists():
            providers_path = PROJECT_ROOT / "config" / "providers.json"

        if providers_path.exists():
            with open(providers_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            result: list[dict[str, Any]] = data.get("providers", [])
            return result
        logger.warning("providers.json not found.")
        return []

    def load_models(self) -> dict[str, list[dict[str, Any]]]:
        """Load model catalog from models.json."""
        models_path = get_jarvis_home() / "config" / "models.json"
        if not models_path.exists():
            models_path = PROJECT_ROOT / "config" / "models.json"

        if models_path.exists():
            with open(models_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            result: dict[str, list[dict[str, Any]]] = data.get("models", {})
            return result
        logger.warning("models.json not found.")
        return {}


def save_api_key_to_env(env_var_name: str, key_value: str) -> None:
    """Save an API key to os.environ and persist it to ~/.jarvis/.env and repo .env."""
    os.environ[env_var_name] = key_value

    env_paths = [
        get_jarvis_home() / ".env",
        PROJECT_ROOT / ".env",
    ]

    for env_path in env_paths:
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            lines: list[str] = []
            if env_path.exists():
                with open(env_path, encoding="utf-8") as f:
                    lines = f.readlines()

            updated = False
            new_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(f"{env_var_name}=") or stripped.startswith(f"export {env_var_name}="):
                    new_lines.append(f"{env_var_name}={key_value}\n")
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines.append("\n")
                new_lines.append(f"{env_var_name}={key_value}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            logger.info(f"Saved API key for {env_var_name} to {env_path}")
        except Exception as e:
            logger.warning(f"Failed to persist API key to {env_path}: {e}")
