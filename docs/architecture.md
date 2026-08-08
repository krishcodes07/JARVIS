# JARVIS Architecture

## Overview

JARVIS is built as a modular, production-grade AI assistant package with a clean separation of concerns. It orchestrates LLM providers, local memory systems, built-in tool execution, Model Context Protocol (MCP) servers, audio processing (voice), and multiple presentation UIs (TUI, Web UI, Desktop GUI).

## Subsystem Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       User Interfaces                           │
│       TUI (Textual)   │   Web UI (FastAPI)   │   Desktop GUI    │
├─────────────────────────────────────────────────────────────────┤
│                       Core Engine                               │
│       Session ←→ Event Bus ←→ Config Manager ←→ Logger          │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  Providers   │    Memory    │    Tools     │    MCP Subsystem   │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌────────────────┐ │
│ │  OpenAI  │ │ │  Conv.   │ │ │  Basic   │ │ │  MCP Client    │ │
│ │Anthropic │ │ │ L-Term   │ │ │ System   │ │ │  MCP Manager   │ │
│ │  Google  │ │ │  Vector  │ │ │ Sandbox  │ │ │ Stdio/NPX Srvr │ │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │ └────────────────┘ │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                       Voice Subsystem                           │
│      Edge TTS / ElevenLabs  ←→  Google STT / Faster-Whisper     │
├─────────────────────────────────────────────────────────────────┤
│                   System Prompt / Persona                       │
└─────────────────────────────────────────────────────────────────┘
```

## Subsystems Detail

- **Core Engine (`src/jarvis/core`)**: Manages the event bus, session state, application lifecycle, error handling, and configuration loading.
- **Provider Manager (`src/jarvis/providers`)**: Handles API authentication, message streaming, token budgets, and fallback provider routing across 180+ LLM providers via `models.dev` catalog (OpenAI, Anthropic, Google Gemini, Groq, NVIDIA NIM, OpenRouter, Mistral, OpenCode, TokenRouter, Kilo, Cerebras, etc.).
- **Memory Manager (`src/jarvis/memory`)**:
  - **Conversation Memory**: Short-term session context with automatic summarization.
  - **Long-Term Memory**: Autonomous fact extraction and storage in JSON format.
  - **Vector Memory**: Semantic search and document RAG powered by ChromaDB.
- **Tool Engine (`src/jarvis/tools`)**: Includes basic utilities (calculator, clipboard, datetime, screenshot, url_reader) and system control tools (`run_command`, `process_manager`, `system_info`) running inside an optional security sandbox.
- **MCP Manager (`src/jarvis/mcp`)**: Native Client & Manager for standard Model Context Protocol servers (Gmail, Calendar, Excel, Telegram, Terminal, Filesystem, Firecrawl, Vercel).
- **Voice Manager (`src/jarvis/voice`)**: Streaming text-to-speech (Edge TTS, ElevenLabs) and speech-to-text input (Google STT, Sphinx, Vosk, faster-whisper).
- **UI Abstraction (`src/jarvis/ui`)**: Supports Textual-based TUI, FastAPI + WebSockets Web UI, and CustomTkinter Desktop GUI.

## Data Flow

1. **User Input** → User Interface (TUI/Web/GUI) → Core Engine
2. **Context Assembly** → Retrieve short-term history + query RAG/Vector memory + inject persona system prompt
3. **LLM Invocation** → Provider Manager selects active model (or triggers fallback) → Stream responses
4. **Tool / MCP Execution** → Parse function calls → Execute tool or MCP server operation → Return observation to LLM
5. **Memory & UI Update** → Persist conversation & extracted facts → Render stream to UI / audio output

## Key Design Decisions

- **Protocol Adapter Pattern**: Shared protocol handlers (e.g. `openai.py`) support multiple compatible provider backends.
- **Asynchronous Event Bus**: Decoupled, non-blocking communication between UIs, voice loop, engine, and tools.
- **Zero-Code Provider Addition**: New OpenAI-compatible endpoints can be declared in `config/providers.json`.
- **Strict Pydantic Validation**: Configuration files (`config/jarvis.yaml`) are validated on boot.
