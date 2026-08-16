# JARVIS Architecture

## Overview

JARVIS is built as a modular, production-grade AI assistant package with a clean separation of concerns. It orchestrates LLM providers, local memory systems, built-in tool execution, Model Context Protocol (MCP) servers, messaging bridges (Telegram & Discord), audio processing (voice), specialized autonomous skills, and multiple presentation UIs (TUI, Web UI, Desktop GUI).

## Subsystem Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           User Interfaces & Entrypoints                         │
│   TUI (Textual)  │  Web UI (FastAPI)  │  Desktop GUI  │  CLI Standalone Service │
├─────────────────────────────────────────────────────────────────────────────────┤
│                               Messaging Connectors                              │
│             TelegramConnector         │          DiscordConnector               │
│                               ConnectorManager                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                  Core Engine                                    │
│             Session  ←→  Event Bus  ←→  Config Manager  ←→  Logger              │
├──────────────┬──────────────┬──────────────┬────────────────────┬───────────────┤
│  Providers   │    Memory    │    Tools     │    MCP Subsystem   │    Skills     │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌────────────────┐ │ ┌───────────┐ │
│ │  OpenAI  │ │ │  Conv.   │ │ │  Basic   │ │ │  MCP Client    │ │ │  Coding   │ │
│ │Anthropic │ │ │ L-Term   │ │ │ Filesyst │ │ │  MCP Manager   │ │ │Bug-Hunting│ │
│ │  Google  │ │ │  Vector  │ │ │ System   │ │ │ Stdio/NPX Srvr │ │ │Code-Review│ │
│ │models.dev│ │ │ ChromaDB │ │ │ Sandbox  │ │ │                │ │ │ Research  │ │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │ └────────────────┘ │ └───────────┘ │
├──────────────┴──────────────┴──────────────┴────────────────────┴───────────────┤
│                                Voice Subsystem                                  │
│         Edge TTS / ElevenLabs   ←→   Google STT / Faster-Whisper                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                             System Prompt / Persona                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Subsystems Detail

- **Core Engine (`src/jarvis/core`)**: Manages the event bus, session state, application lifecycle, error handling, and multi-location configuration loading (`~/.jarvis/config/jarvis.yaml` and `config/jarvis.yaml`).
- **Messaging Connectors (`src/jarvis/connectors`)**: Multi-platform chat bridges (Telegram, Discord) enabling 24/7 conversational assistant interaction with user/channel allowlists, bot commands (`/session`, `/new`, `/clear`, `/status`, `/help`), and standalone background execution.
- **Provider Manager (`src/jarvis/providers`)**: Handles API authentication, message streaming, token budgets, and fallback provider routing across 180+ LLM providers via `models.dev` catalog (OpenAI, Anthropic, Google Gemini, Groq, NVIDIA NIM, OpenRouter, Mistral, OpenCode, TokenRouter, Kilo, Cerebras, etc.).
- **Skills Subsystem (`src/jarvis/skills`)**: Pluggable autonomous skills for coding, bug hunting, code review, data analysis, deep research, and system architecture.
- **Memory Manager (`src/jarvis/memory`)**:
  - **Conversation Memory**: Short-term session context with automatic summarization.
  - **Long-Term Memory**: Autonomous fact extraction and storage in JSON format.
  - **Vector Memory**: Semantic search and document RAG powered by ChromaDB.
- **Tool Engine (`src/jarvis/tools`)**: Includes basic utilities (calculator, clipboard, datetime, screenshot, url_reader), filesystem operations, and system control tools (`run_command`, `process_manager`, `system_info`) running inside an optional security sandbox.
- **MCP Manager (`src/jarvis/mcp`)**: Native Client & Manager for standard Model Context Protocol servers (Gmail, Calendar, Excel, Telegram, Terminal, Filesystem, Firecrawl, Vercel).
- **Voice Manager (`src/jarvis/voice`)**: Streaming text-to-speech (Edge TTS, ElevenLabs) and speech-to-text input (Google STT, Sphinx, Vosk, faster-whisper).
- **UI Abstraction (`src/jarvis/ui`)**: Supports Textual-based TUI, FastAPI + WebSockets Web UI, and CustomTkinter/PySide6 Desktop GUI.

## Data Flow

1. **User Input** → User Interface (TUI/Web/GUI) or Messaging Connector (Telegram/Discord) → Core Engine
2. **Context Assembly** → Retrieve short-term history + query RAG/Vector memory + inject persona system prompt & active skills
3. **LLM Invocation** → Provider Manager selects active model (or triggers fallback) → Stream responses
4. **Tool / MCP Execution** → Parse function calls → Execute tool or MCP server operation → Return observation to LLM
5. **Memory & UI Update** → Persist conversation & extracted facts → Render stream to UI / connector reply / audio output

## Key Design Decisions

- **Protocol Adapter Pattern**: Shared protocol handlers (e.g. `openai.py`) support multiple compatible provider backends.
- **Asynchronous Event Bus**: Decoupled, non-blocking communication between UIs, connectors, voice loop, engine, and tools.
- **Zero-Code Provider Addition**: New OpenAI-compatible endpoints can be declared in `config/providers.json`.
- **Hierarchical Configuration**: Config files support user-home seeding (`~/.jarvis/config/jarvis.yaml`), project fallbacks, and strict Pydantic v2 validation.
