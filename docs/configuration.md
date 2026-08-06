# Configuration Reference

JARVIS relies on a multi-tiered, dynamic configuration system consisting of YAML settings, JSON provider/server registries, and environment variable overrides.

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| **Main Config** | `config/jarvis.yaml` | Core settings (provider selection, memory, tools, voice, UI options) |
| **Providers Registry** | `config/providers.json` | API endpoints, model IDs, protocols, and supported capabilities |
| **MCP Servers Registry** | `src/jarvis/mcp/servers.json` | Registered MCP stdio and npx server command definitions |
| **Environment Variables** | `.env` | Provider API keys, secret credentials, and private tokens |

---

## `jarvis.yaml` Configuration Reference

Below is a breakdown of the primary configuration blocks:

### 1. `jarvis`
General application metadata:
- `name`: Persona display name (default: `JARVIS/`).
- `version`: Version string (e.g. `0.1.0`).
- `persona`: Persona template key (`professional_assistant`).
- `log_level`: Console/file log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

### 2. `provider`
Active LLM model routing and fallback configuration:
- `active`: Key matching a provider in `providers.json` (e.g. `opencode-zen`, `groq`, `openai`, `anthropic`).
- `model`: Target model ID.
- `temperature`: Generation temperature (0.0 to 1.0).
- `max_tokens`: Max tokens per response context.
- `fallback.enabled`: Enable automatic failover to a backup provider upon API errors.
- `fallback.provider` / `fallback.model`: Fallback backend credentials.

### 3. `memory`
Multi-tiered memory system options:
- `conversation`: Short-term chat history tracking & automatic summarization threshold (`summarize_after`).
- `long_term`: Fact extraction settings (`auto_extract`, `provider`, `storage_path`).
- `vector`: RAG storage settings (`backend`, `embedding_provider`, `embedding_model`, `storage_path`, `knowledge_base_path`).

### 4. `tools`
Execution rules for built-in tools:
- `enabled`: Global toggle for tool execution.
- `auto_approve`: Auto-confirm non-dangerous tool invocations.
- `max_turns`: Max tool execution loop iterations per user prompt.
- `sandbox.enabled`: Restrict system calls and file access to designated workspace directories.

### 5. `mcp`
Model Context Protocol integration:
- `enabled`: Toggle MCP server discovery and tool binding.
- `auto_start`: List of server names to initialize automatically on startup.
- `servers_config`: Path to `src/jarvis/mcp/servers.json`.

### 6. `voice`
Speech input and output settings:
- `enabled`: Master switch for audio and voice loops.
- `mode`: Operating mode (`text` or `voice`).
- `tts`: Provider (`edge_tts`, `elevenlabs`), active voice ID, rate, pitch, streaming flags.
- `stt`: Provider (`sr`, `whisper`), engine (`google`, `sphinx`, `vosk`), sample rate, energy thresholds.

### 7. `ui`
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

# MCP & Service Keys
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
TELEGRAM_BOT_TOKEN=
FIRECRAWL_API_KEY=

# Voice
ELEVENLABS_API_KEY=
```
