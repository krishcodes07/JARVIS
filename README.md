<div align="center">

<table align="center">
<tr><td align="center">

```
 ██████╗  █████╗ ██████╗ ██╗   ██╗██╗███████╗
 ╚══██╔╝ ██╔══██╗██╔══██╗██║   ██║██║██╔════╝
    ██║  ███████║██████╔╝██║   ██║██║███████╗
██  ██║  ██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝ ██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝  ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

</td></tr>
</table>

<p align="center"><b>Just A Rather Very Intelligent System</b></p>
<p align="center"><b>The ultimate open-source AI assistant. Multi-provider, MCP-powered, voice-enabled.</b></p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11.4+" src="https://img.shields.io/badge/python-3.11.4%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" /></a>
  <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="https://textual.textualize.io"><img alt="Textual TUI" src="https://img.shields.io/badge/TUI-Textual-blueviolet?style=for-the-badge" /></a>
  <a href="https://modelcontextprotocol.io"><img alt="MCP Supported" src="https://img.shields.io/badge/MCP-1.0-purple?style=for-the-badge" /></a>
  <a href="https://github.com/krishcodes07/JARVIS"><img alt="Status: Active Alpha" src="https://img.shields.io/badge/status-active_alpha-orange?style=for-the-badge" /></a>
</p>

</div>

[![JARVIS Terminal UI Preview](tui_preview.png)](tui_preview.png)

> [!IMPORTANT]
> **Project Development Status**: Currently, **only the Terminal UI (TUI)** is active and under active development. The **Web UI** and **Desktop GUI** are currently in the development phase and are not functional yet.

---

## Why J.A.R.V.I.S.?

Most AI assistants lock you into a single provider, restrict your choice of interfaces, or hide key infrastructure behind vendor paywalls. **JARVIS gives you absolute control over your AI environment.** Query 180+ LLM providers via `models.dev` integration, interact via rich terminal TUI, extend functionality with Model Context Protocol (MCP) servers, and control everything hands-free with real-time streaming voice.

- **180+ LLM Provider Catalog (`models.dev`)** — Direct integration with 180+ LLM providers (OpenAI, Anthropic, Google Gemini, Groq, NVIDIA NIM, OpenRouter, Mistral, OpenCode, TokenRouter, Kilo, Cerebras, etc.) with automatic fallback streaming routing.
- **Full PC Control & Autonomous Desktop Automation** — End-to-end multi-step OS control (`/automate`), Windows UI Automation (UIA) tree inspection, dynamic application discovery, smooth mouse/keyboard simulation, and global emergency abort safety (`Ctrl+Alt+Q`).
- **Rich Terminal UI (TUI)** — Interactive Textual-powered terminal application with streaming markdown, syntax highlighting, keyboard shortcuts (`Ctrl+M` model picker, `Ctrl+A` API key modal), and voice toggle.
- **Multi-Platform Messaging Connectors** — Bi-directional bot bridges for **Telegram** and **Discord** with user/channel allowlists, bot commands (`/session`, `/new`, `/clear`, `/status`, `/help`), and standalone background service modes.
- **Specialized Skills Framework** — Modular skill packs for autonomous bug hunting, code review, fullstack coding, data analysis, deep research, and system architecture.
- **Native MCP Ecosystem & Creation** — Seamlessly integrate Gmail, Calendar, Excel, Telegram, Filesystem, Terminal, Firecrawl, and Vercel — or let JARVIS generate custom MCP servers dynamically.
- **Integrated Voice Suite** — Natural speech-to-text (STT) input and real-time streaming text-to-speech (TTS) output with hands-free conversation mode.

---

## User Interfaces & Technical Stack

| Component | Interface / Subsystem | Status | Technical Stack |
| --- | --- | --- | --- |
| **Terminal UI (TUI)** | Rich TUI Application | 🟢 **Active (In Dev)** | Python 3.11.4, Textual, Rich Markdown |
| **Desktop Automation** | Autonomous PC Control & Actuation | 🟢 **Active** | Windows UIA, PyAutoGUI, PyWinAuto, ScreenInfo, Pynput |
| **Messaging Connectors** | Telegram & Discord Bridges | 🟢 **Active** | `python-telegram-bot`, `discord.py`, Asyncio |
| **Web UI** | Web Dashboard | 🟡 *In Development (Non-functional)* | FastAPI, Uvicorn, WebSockets, Jinja2 |
| **Desktop GUI** | Desktop Window | 🟡 *In Development (Non-functional)* | CustomTkinter / PySide6, Asyncio integration |
| **Core Engine** | Orchestration & Events | 🟢 **Active** | Asyncio Event Bus, Pydantic v2 Config |
| **Skills Subsystem** | Specialized Prompt Modules | 🟢 **Active** | Structured prompts, auto-discovery runner |
| **Memory System** | Short & Long-term RAG | 🟢 **Active** | JSON session storage, ChromaDB Vector Store |
| **MCP Manager** | Protocol Integration | 🟢 **Active** | Stdio transport, MCP SDK 1.0+, NPX runners |
| **Voice Suite** | Speech Input / Output | 🟢 **Active** | Edge TTS, ElevenLabs, SpeechRecognition, `faster-whisper` |

---

## Features

- **Autonomous PC Control & Desktop Automation** — Execute multi-step desktop workflows (`/automate <goal>`), launch & control apps, browse websites, manage window layouts (snapping, maximizing), adjust system audio volume, and simulate mouse/keyboard with emergency abort failsafes (`Ctrl+Alt+Q`).
- **Terminal TUI Experience** — Rich, interactive terminal interface (`python main.py`) with real-time streaming, command history, model search modal (`Ctrl+M`), API key connector (`Ctrl+A`), and voice controls.
- **Messaging Connectors (Telegram & Discord)** — Run JARVIS as a 24/7 personal assistant on Telegram and Discord with channel/user allowlists, message chunking, typing indicators, and session persistence.
- **180+ LLM Provider Backends** — Powered by the `models.dev` catalog with automatic provider protocol detection (OpenAI, Anthropic, Google Gemini) and automatic fallback routing upon API errors.
- **Specialized Skills Engine** — Built-in autonomous skills for `coding`, `bug-hunting`, `code-review`, `data-analysis`, `deep-research`, and `system-architecture`.
- **Full Function Calling & Tool Support** — Native tool use support across OpenAI, Anthropic, and Google Gemini APIs (with native `functionCall` and `functionResponse` payload structure).
- **Multi-Tiered Memory & RAG** — Conversation history with automatic summarization, autonomous long-term fact extraction, and vector semantic search powered by ChromaDB.
- **Built-in Tools & Security Sandbox** — Desktop tools (`app_control`, `browser_control`, `window_control`, `media_control`, `system_settings`, `input_simulation`, `automate_task`), filesystem tools, calculator, screenshot generator, and command runner operating inside a configurable security sandbox.
- **Native MCP Integration** — Direct integration with stdio and npx Model Context Protocol servers (Gmail, Calendar, Excel, Telegram, Terminal, Filesystem, Firecrawl, Vercel).
- **Real-time Voice Mode** — Speech-to-text input paired with edge/ElevenLabs text-to-speech streaming for hands-free operation.
- **Fully Configurable** — YAML (`~/.jarvis/config/jarvis.yaml` or `config/jarvis.yaml`), dynamic `models.dev` cache (`data/models_dev_cache.json`), and `.env` credentials.
- **Docker Ready** — Containerized multi-stage Docker build and one-command Docker Compose stack.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/krishcodes07/JARVIS.git
cd JARVIS

# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/Mac

# Install JARVIS core package
pip install -e .

# Copy environment variable template
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac
# Edit .env with your API keys!
```

### Optional Installation Extras

Select extra dependency packages depending on your needs:

```bash
# Install PC Control & Desktop Automation dependencies
pip install -e ".[automation]"

# Install Voice dependencies (Edge TTS, ElevenLabs, SpeechRecognition, faster-whisper)
pip install -e ".[voice]"

# Install MCP server extras (openpyxl for Excel, telethon for Telegram)
pip install -e ".[mcp]"

# Install Developer & Testing tools (pytest, ruff, mypy)
pip install -e ".[dev]"

# Install ALL features at once
pip install -e ".[automation,voice,mcp,dev]"
```

---

## Running JARVIS

### 1. Terminal UI (Active Interactive Interface)

```bash
# Launch interactive TUI
python main.py
# or
python -m jarvis --ui tui

# Launch with Debug Logging
python main.py --debug
```

### 2. Standalone Messaging Connector Services

Run JARVIS as a background messaging bridge service:

```bash
# Run Telegram bot bridge
python -m jarvis --connector telegram

# Run Discord bot bridge
python -m jarvis --connector discord

# Run all enabled messaging bridges simultaneously
python -m jarvis --connector all
```

> [!NOTE]
> Web UI (`--ui web`) and Desktop GUI (`--ui gui`) flags exist in CLI but are currently under development. Please use the TUI (`--ui tui`) interface or the Messaging Connectors (`--connector <name>`).

---

## Supported Providers & Capabilities

| Provider | Protocol | Default Model | Vision | Tools | Streaming | Recommended Env Key |
| --- | --- | --- | :---: | :---: | :---: | --- |
| **OpenAI** | `openai` | `gpt-4o` | ✅ | ✅ | ✅ | `OPENAI_API_KEY` |
| **Anthropic** | `anthropic` | `claude-sonnet-4-20250514` | ✅ | ✅ | ✅ | `ANTHROPIC_API_KEY` |
| **Google Gemini** | `google` | `gemini-2.5-flash` | ✅ | ✅ | ✅ | `GOOGLE_API_KEY` |
| **Groq** | `openai` | `llama-3.3-70b-versatile` | ❌ | ✅ | ✅ | `GROQ_API_KEY` |
| **NVIDIA NIM** | `openai` | `meta/llama-3.1-405b-instruct` | ❌ | ✅ | ✅ | `NVIDIA_API_KEY` |
| **OpenRouter** | `openai` | `anthropic/claude-sonnet-4` | ✅ | ✅ | ✅ | `OPENROUTER_API_KEY` |
| **Mistral AI** | `openai` | `mistral-large-latest` | ✅ | ✅ | ✅ | `MISTRAL_API_KEY` |
| **OpenCode Zen** | `openai` | `deepseek-v4-flash-free` | ❌ | ✅ | ✅ | `OPENCODE_ZEN_API_KEY` |
| **TokenRouter** | `openai` | `moonshotai/kimi-k3-free` | ❌ | ✅ | ✅ | `TOKENROUTER_API_KEY` |

> [!TIP]
> To add a new OpenAI-compatible provider, simply add an entry to `config/providers.json` — zero code changes required!

---

## Built-in Tools & Security Sandboxing

JARVIS includes out-of-the-box tools categorized by safety levels:

- **Desktop Control Tools**: `app_control`, `browser_control`, `window_control`, `media_control`, `system_settings`, `input_simulation`, `automate_task`
- **Basic Tools**: `calculator`, `clipboard`, `datetime_tool`, `screenshot`, `url_reader`
- **Filesystem Tools**: `read_file`, `write_file`, `edit_file`, `append_file`, `list_directory`, `make_directory`, `delete_file`, `copy_file`, `move_file`, `search_files`, `grep_search`, `get_file_info`
- **System Tools**: `process_manager`, `run_command`, `system_info`

### Permissions & Sandboxing

JARVIS enforces safety constraints when executing system commands and desktop actions:
- **Sandbox Restrictions**: Workspace isolation and blocking of dangerous shell commands.
- **Desktop Emergency Abort**: Press `Ctrl+Alt+Q` at any time to instantly freeze and abort autonomous desktop automation.
- **Protected Applications**: Automatic refusal to actuate inside sensitive windows (e.g. password managers, security prompts).

```yaml
tools:
  categories:
    desktop: true
    filesystem: true
    system: true
    basic: true
  sandbox:
    enabled: true
    workspace: "."
    blocked_commands: ["rm -rf /", "format", "shutdown"]
```

---

## MCP (Model Context Protocol) Ecosystem

JARVIS features native Model Context Protocol support out-of-the-box:

| Server | Transport | Description | Status |
| --- | --- | --- | --- |
| 📧 **Gmail** | `stdio` | Send, read, search emails, and manage message threads | Built-in |
| 📅 **Calendar** | `stdio` | Manage events, meetings, schedules, and reminders | Built-in |
| 📊 **Excel** | `stdio` | Read, edit, format, and analyze `.xlsx` spreadsheets | Built-in |
| 💬 **Telegram** | `stdio` | Send and receive Telegram chat messages | Built-in |
| 🖥️ **Terminal** | `stdio` | Inspect system processes and run shell commands | Built-in |
| 🔍 **Firecrawl** | `stdio (npx)` | Real-time web scraping, crawling, and search | External |
| 🚀 **Vercel** | `stdio (npx)` | Manage deployments, domains, and analytics | External |

---

## Multi-Platform Messaging Connectors

JARVIS can be deployed as a personal AI bot across chat channels with full access to tools, memory, and models:

| Platform | Connector | Configuration | Supported Features |
| --- | --- | --- | --- |
| ✈️ **Telegram** | `TelegramConnector` | `connectors.telegram.enabled: true` | Long-polling, typing action, user allowlist, slash commands |
| 👾 **Discord** | `DiscordConnector` | `connectors.discord.enabled: true` | Channel / Guild / User allowlists, typing indicator, message splitting |

### Connector In-Chat Commands
All connectors support built-in command handlers:
- `/session [id]` — Switch or view current chat session.
- `/new` — Spawn a brand new independent conversation session.
- `/clear` — Wipe session history and start clean.
- `/status` — View connector uptime, current LLM model, and system health.
- `/help` — List available connector bot commands.

---

## Specialized Skills Framework

JARVIS includes pluggable, specialized skill engines located under `src/jarvis/skills/`:

- 🐛 **`bug-hunting`** — Autonomous reproduction, root-cause debugging, hypothesis testing, and regression analysis.
- 🔍 **`code-review`** — Automated code quality, security vulnerability auditing, and adherence to design patterns.
- 💻 **`coding`** — Full-stack implementation, architecture scaffolding, refactoring, and clean code generation.
- 📊 **`data-analysis`** — Exploratory data analysis, statistical breakdowns, and data visualization planning.
- 🔬 **`deep-research`** — Recursive multi-source investigation, source synthesis, and executive briefing reports.
- 🏛️ **`system-architecture`** — High-level distributed system design, API contracts, and scalability modeling.

---

## Voice Suite & Commands

JARVIS includes a full hands-free voice suite:

- **Text-to-Speech (TTS)**: Free streaming via `edge_tts` or high-fidelity AI voices with `elevenlabs`.
- **Speech-to-Text (STT)**: `SpeechRecognition` engines (Google, Sphinx, Vosk) or local offline STT with `faster-whisper`.

### Terminal UI Slash Commands

JARVIS TUI supports rich interactive slash commands:

- `/automate <goal>` or `/pc <goal>` — Run an autonomous multi-step PC desktop automation workflow.
- `/new` — Start a new conversation session with a unique session ID.
- `/clear` — Reset conversation, delete current session, and start a fresh session (with top-right notification toast).
- `/copy` — Copy the last AI assistant response directly to system clipboard silently.
- `/models` — Open model selection modal or switch active LLM model.
- `/sessions` — Manage and switch active conversation sessions.
- `/mcp` — Open MCP server manager modal and inspect connections.
- `/voice` — Toggle hands-free voice mode on/off.
- `/tts <provider>` — Switch TTS provider (`edge_tts` / `elevenlabs`).
- `/stt <provider>` — Switch STT provider (`sr` / `whisper`).
- `/voices` — List available TTS voices.
- `/config` — View and edit active runtime configuration.
- `/debug` — Inspect system status, provider metrics, and event diagnostics.
- `/help` — Display commands overview and keybindings.

---

## Docker Deployment

Deploy containerized JARVIS with Docker Compose:

```bash
# Build and run Docker container
docker compose up --build
```

---

## Documentation

| Topic | Link |
| --- | --- |
| **System Architecture** | [docs/architecture.md](docs/architecture.md) |
| **Getting Started Guide** | [docs/getting_started.md](docs/getting_started.md) |
| **Configuration Reference** | [docs/configuration.md](docs/configuration.md) |
| **Adding a Provider** | [docs/guides/adding_providers.md](docs/guides/adding_providers.md) |
| **Creating Custom Tools** | [docs/guides/creating_tools.md](docs/guides/creating_tools.md) |
| **Creating MCP Servers** | [docs/guides/creating_mcp_servers.md](docs/guides/creating_mcp_servers.md) |
| **Contributing Guidelines** | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## Testing & Quality

Run the automated test suite, linter, and static type checker:

```bash
# Run pytest unit and integration tests
pytest

# Check code formatting & linting
ruff check .

# Run static type checking
mypy src/jarvis

# Build distribution package
python scripts/build.py
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

*"At your service, sir."* — J.A.R.V.I.S.

</div>
