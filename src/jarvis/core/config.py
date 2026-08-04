"""
JARVIS Configuration — Loads and manages all configuration.

Configuration sources (in priority order):
1. Environment variables (.env)
2. YAML config file (config/jarvis.yaml)
3. JSON config files (config/providers.json, config/models.json)
4. Default values
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ─── Project root detection ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/jarvis/core -> project root
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


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
    storage_path: str = "data/long_term_memory"


class VectorMemoryConfig(BaseModel):
    """Vector / semantic memory settings."""
    enabled: bool = True
    backend: str = "chromadb"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 512
    chunk_overlap: int = 50
    collection_name: str = "jarvis_memory"
    storage_path: str = "data/vector_store"
    knowledge_base_path: str = "data/knowledge_base"


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


class ToolRAGConfig(BaseModel):
    """Tool RAG (semantic tool selection) settings."""
    enabled: bool = True
    top_k: int = 8
    always_include: list[str] = Field(
        default_factory=lambda: ["run_command", "calculator", "get_mcps", "get_tools"]
    )


class ToolsConfig(BaseModel):
    """Tool system settings."""
    enabled: bool = True
    auto_approve: bool = False
    max_turns: int = 25
    timeout: int = 30
    max_retries: int = 2
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    rag: ToolRAGConfig = Field(default_factory=ToolRAGConfig)
    categories: dict[str, bool] = Field(
        default_factory=lambda: {"basic": True, "filesystem": True, "system": True, "code": True}
    )



class MCPConfig(BaseModel):
    """MCP subsystem settings.

    All servers under ``src/jarvis/mcp/servers/`` are auto-registered and
    enabled by default. Use ``servers`` to enable/disable or override
    individual servers from ``jarvis.yaml``:

    .. code-block:: yaml

        mcp:
          enabled: true
          servers:
            gmail:
              enabled: false          # disable a server
            telegram:
              command: python         # override launch config
              env:
                TELEGRAM_API_ID: "..."
    """

    enabled: bool = True
    auto_start: list[str] = Field(default_factory=list)
    timeout: int = 30
    servers_config: str = "src/jarvis/mcp/servers.json"
    servers: dict[str, MCPServerOverride] = Field(default_factory=dict)

    @field_validator("servers", mode="before")
    @classmethod
    def _coerce_servers(cls, value: Any) -> Any:
        """Coerce an empty ``servers:`` key (only comments) to an empty dict."""
        if value is None:
            return {}
        return value


class MCPServerOverride(BaseModel):
    """Per-server MCP override config (from ``jarvis.yaml``)."""

    enabled: bool | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] = Field(default_factory=dict)
    transport: str | None = None
    timeout: int | None = None
    description: str | None = None
    url: str | None = None


class TUIConfig(BaseModel):
    """TUI settings."""
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


class VoiceAudioConfig(BaseModel):
    """Audio device settings for the voice subsystem."""
    input_device: str | int | None = None      # microphone device (None = default)
    output_device: str | int | None = None     # speaker device (None = default)
    sample_rate: int = 44100                   # playback sample rate (Hz)


class VoiceConfig(BaseModel):
    """Voice subsystem settings (TTS / STT / audio)."""
    enabled: bool = True
    mode: str = "text"                         # text | voice (default mode)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    audio: VoiceAudioConfig = Field(default_factory=VoiceAudioConfig)


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
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> JarvisConfig:
        """Load configuration from YAML file and environment.

        Args:
            config_path: Path to jarvis.yaml. If None, uses default location.

        Returns:
            Fully loaded JarvisConfig instance.
        """
        # Load .env file
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")

        # Load YAML config
        if config_path is None:
            config_path = CONFIG_DIR / "jarvis.yaml"

        if config_path.exists():
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
            config_path: Path to save to. If None, uses default location.
        """
        if config_path is None:
            config_path = CONFIG_DIR / "jarvis.yaml"

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
        """Get an API key from environment variables.

        Args:
            env_var: The environment variable name.

        Returns:
            The API key value, or None if not set.
        """
        return os.getenv(env_var)

    def load_providers(self) -> list[dict[str, Any]]:
        """Load provider definitions from providers.json.

        Returns:
            List of provider configuration dictionaries.
        """
        providers_path = CONFIG_DIR / "providers.json"
        if providers_path.exists():
            with open(providers_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("providers", [])
        logger.warning("providers.json not found.")
        return []

    def load_models(self) -> dict[str, list[dict[str, Any]]]:
        """Load model catalog from models.json.

        Returns:
            Dictionary mapping provider names to lists of model configs.
        """
        models_path = CONFIG_DIR / "models.json"
        if models_path.exists():
            with open(models_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("models", {})
        logger.warning("models.json not found.")
        return {}
