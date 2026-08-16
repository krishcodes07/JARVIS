# Configuration Reference

JARVIS relies on a multi-tiered, dynamic configuration system consisting of YAML settings, JSON provider/server registries, and environment variable overrides.

## Configuration Resolution Order

When JARVIS boots, configuration is discovered and loaded in the following order:
1. **Explicit CLI Path**: `--config /path/to/jarvis.yaml`
2. **User Home Config Directory**: `~/.jarvis/config/jarvis.yaml` (seeded automatically on first run)
3. **Repository Workspace Config**: `config/jarvis.yaml`
4. **Pydantic Defaults**: Safe built-in defaults with environment variable overrides.

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| **User Main Config** | `~/.jarvis/config/jarvis.yaml` | Core settings (provider selection, connectors, memory, tools, voice, UI options) |
| **Repo Main Config** | `config/jarvis.yaml` | Workspace-level fallback settings |
| **models.dev Cache** | `data/models_dev_cache.json` | Local cache of 180+ LLM providers and model catalogs from models.dev |
| **MCP Servers Registry** | `src/jarvis/mcp/servers.json` | Registered MCP stdio and npx server command definitions |
| **Environment Variables** | `.env` | Provider API keys, secret credentials, and private tokens |

---

## `jarvis.yaml` Configuration Reference

Below is a breakdown of the primary configuration blocks:

### 1. `jarvis`
General application metadata:
- `name`: Persona display name (default: `JARVIS`).
- `version`: Version string (e.g. `0.1.0`).
- `persona`: Persona template key (`professional_assistant`).
- `log_level`: Console/file log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

### 2. `provider`
Active LLM model routing and fallback configuration:
- `active`: Key matching a provider in models.dev catalog (e.g. `opencode`, `groq`, `openai`, `anthropic`, `google`, `kilo`).
- `model`: Target model ID.
- `temperature`: Generation temperature (0.0 to 1.0).
- `max_tokens`: Max tokens per response context.
- `fallback.enabled`: Enable automatic failover to a backup provider upon API errors.
- `fallback.provider` / `fallback.model`: Fallback backend credentials.

### 3. `connectors`
Multi-platform chat bridge settings (Telegram, Discord):
- `enabled`: Master switch for the messaging connectors subsystem.
- `telegram`:
  - `enabled`: Enable Telegram bot connector.
  - `bot_token`: Telegram Bot API token (or set via `TELEGRAM_BOT_TOKEN` env).
  - `allowed_users`: List of allowed user IDs or usernames (empty = allow all).
  - `polling_timeout`: Long polling timeout in seconds (default: `30`).
  - `send_typing`: Send typing action while generating responses.
  - `max_message_length`: Message character chunking limit (default: `4000`, max `4096`).
- `discord`:
  - `enabled`: Enable Discord bot connector.
  - `bot_token`: Discord Bot Token (or set via `DISCORD_BOT_TOKEN` env).
  - `allowed_channels`: Channel ID allowlist.
  - `allowed_users`: User ID allowlist.
  - `allowed_guilds`: Server / Guild ID allowlist.
  - `send_typing`: Show typing indicator while generating responses.
  - `max_message_length`: Message character chunking limit (default: `2000`).

### 4. `memory`
Multi-tiered memory system options:
- `conversation`: Short-term chat history tracking & automatic summarization threshold (`summarize_after`).
- `long_term`: Fact extraction settings (`auto_extract`, `provider`, `storage_path`).
- `vector`: RAG storage settings (`backend`, `embedding_provider`, `embedding_model`, `storage_path`, `knowledge_base_path`).

### 5. `tools`
Execution rules for built-in tools:
- `enabled`: Global toggle for tool execution.
- `auto_approve`: Auto-confirm non-dangerous tool invocations.
- `max_turns`: Max tool execution loop iterations per user prompt.
- `sandbox.enabled`: Restrict system calls and file access to designated workspace directories.

### 6. `mcp`
Model Context Protocol integration:
- `enabled`: Toggle MCP server discovery and tool binding.
- `auto_start`: List of server names to initialize automatically on startup.
- `servers_config`: Path to `src/jarvis/mcp/servers.json`.

### 7. `voice`
Speech input and output settings:
- `enabled`: Master switch for audio and voice loops.
- `mode`: Operating mode (`text` or `voice`).
- `tts`: Provider (`edge_tts`, `elevenlabs`), active voice ID, rate, pitch, streaming flags.
- `stt`: Provider (`sr`, `whisper`), engine (`google`, `sphinx`, `vosk`), sample rate, energy thresholds.

### 8. `ui`
Default UI preference (`default: tui`) and theme configurations for `tui`, `web`, and `gui`.

---

## Environment Variables (`.env`)

```env
# LLM Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
GROQ_API_KEY=gsk_...
NVIDIA_API_KEY=nvapi-...
OPENROUTER_API_KEY=sk-or-...
MISTRAL_API_KEY=...
OPENCODE_ZEN_API_KEY=...
TOKENROUTER_API_KEY=...

# Messaging Connectors
TELEGRAM_BOT_TOKEN=
DISCORD_BOT_TOKEN=

# MCP & Service Keys
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
FIRECRAWL_API_KEY=

# Voice
ELEVENLABS_API_KEY=
```
