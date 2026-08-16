# Changelog

All notable changes to JARVIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Multi-Platform Messaging Connectors**:
  - `TelegramConnector`: Native long-polling bridge with typing indicator, message chunking, allowlist security, and session routing.
  - `DiscordConnector`: Full discord.py bot bridge with guild/channel/user allowlists, typing triggers, and multi-message splitting.
  - `ConnectorManager`: Central discovery and orchestration engine for messaging bridges.
  - Built-in in-chat connector commands: `/session`, `/new`, `/clear`, `/status`, `/help`.
  - Standalone service CLI runner: `python -m jarvis --connector {telegram,discord,all}`.
- **Specialized Skills Framework**:
  - Modular skill pack engine in `src/jarvis/skills/`.
  - Built-in skills for `coding`, `bug-hunting`, `code-review`, `data-analysis`, `deep-research`, and `system-architecture`.
- **180+ Provider Catalog (`models.dev`)**:
  - Automatic protocol resolution (OpenAI, Anthropic, Google Gemini).
  - Robust fallback routing mechanism upon API errors.
- **User Home Configuration**:
  - Auto-seeding and loading from `~/.jarvis/config/jarvis.yaml`.
- **Core Engine & Memory Subsystem**:
  - Short-term conversation history with automatic summarization.
  - Long-term memory extraction and ChromaDB vector RAG store.
  - Built-in tool sandbox with safety constraint verification.
- **Model Context Protocol (MCP)**:
  - Native stdio client and npx process runner for external tools (Gmail, Calendar, Excel, Telegram, Filesystem, Terminal, Firecrawl, Vercel).
- **Voice Suite**:
  - Edge TTS and ElevenLabs text-to-speech streaming.
  - SpeechRecognition engines and local faster-whisper speech-to-text.
- **Terminal User Interface (TUI)**:
  - Rich Textual interface with real-time markdown streaming, syntax highlighting, and modals (`Ctrl+M`, `Ctrl+A`, `Ctrl+P`, `Ctrl+V`).

### Removed
- Removed temporary WhatsApp Cloud API connector stub from core package, configuration schemas, and CLI options.
