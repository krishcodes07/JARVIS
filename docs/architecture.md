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

- **Core Engine (`src/jarvis/core`)**: Manages the event bus, session state, application lifecycle, error handling, and user-isolated configuration (`~/.jarvis/config/jarvis.yaml`).
- **Setup & Validation (`src/jarvis/setup`)**: Interactive onboarding wizard validating live provider endpoints, testing models without token costs, and verifying offline vector embeddings.
- **Authentication & OAuth Loopback (`src/jarvis/mcp/auth`)**: RFC 8252 compliant native browser OAuth 2.0 loopback server with PKCE (for Google Gmail and Calendar) and persistent encrypted token management (`~/.jarvis/auth/tokens.json`).
- **Messaging Connectors (`src/jarvis/connectors`)**: Auto-discovered multi-platform chat bridges (Telegram, Discord, and user-defined packages in `~/.jarvis/connectors/`) enabling 24/7 assistant operation with allowlists, slash commands, and standalone runner mode.
- **Provider Manager (`src/jarvis/providers`)**: Handles API authentication, message streaming, token budgets, and automated fallback routing across 180+ LLM providers via dynamic `models.dev` catalog integration.
- **Skills Subsystem (`src/jarvis/skills`)**: Pluggable autonomous skills for coding, bug hunting, code review, data analysis, deep research, frontend design, MCP creation, and system architecture.
- **Memory Manager (`src/jarvis/memory`)**:
  - **Conversation Memory**: Short-term session context with automatic summarization.
  - **Long-Term Memory**: Autonomous fact extraction and storage in JSON format.
  - **Vector Memory**: Semantic search powered by ChromaDB, supporting both remote embedding APIs and bundled offline ONNX `all-MiniLM-L6-v2` embeddings.
- **Tool Engine (`src/jarvis/tools`)**: Includes basic utilities, desktop automation, dynamic MCP server creator (`mcp_creator`), filesystem operations, and system control tools running inside an optional security sandbox.
- **MCP Subsystem (`src/jarvis/mcp`)**: Native Client & Manager for standard Model Context Protocol servers with dynamic registration and template generation.
- **Voice Manager (`src/jarvis/voice`)**: Streaming text-to-speech (Edge TTS, ElevenLabs) with sentence/paragraph chunking and speech-to-text input (Google STT, Sphinx, Vosk, faster-whisper).
- **UI Abstraction (`src/jarvis/ui`)**:
  - **Terminal UI (TUI)**: Textual-based terminal application with in-app modals (Model Picker, API Key Connector, MCP Manager, Themes, Reasoning Effort).
  - **Web UI (React SPA + FastAPI)**: Single-page application built with React 18, TypeScript, Tailwind CSS, Framer Motion, and ThreeUI WebGL procedural backgrounds, communicating over WebSocket streaming (`/ws/chat`) and REST APIs (`/api/`) with browser-native real-time STT and audio visualizers. See [Web UI Guide](guides/web_ui.md).
  - **Desktop GUI**: Desktop interface (in development).

## Data Flow

1. **User Input** → User Interface (TUI/Web/GUI) or Messaging Connector (Telegram/Discord) → Core Engine
2. **Context Assembly** → Retrieve short-term history + query RAG/Vector memory (local or remote) + inject persona system prompt & active skills
3. **LLM Invocation** → Provider Manager selects active model (or triggers fallback) → Stream responses & extract `<think>` blocks
4. **Tool / MCP Execution** → Parse function calls → Execute tool or MCP server operation → Return observation to LLM
5. **Memory & UI Update** → Persist conversation & extracted facts → Render stream to UI / connector reply / audio output

## Key Design Decisions

- **Protocol Adapter Pattern**: Unified protocol handlers (`openai`, `anthropic`, `google`) power 180+ providers.
- **Dynamic Plugin & Connector Discovery**: Connectors and tools are discovered from disk at runtime rather than hardcoded lists.
- **Zero-Config Offline Embedding**: ChromaDB's bundled ONNX model is used when no remote embedding key is supplied.
- **RFC 8252 OAuth Loopback**: Interactive native browser OAuth eliminates the need for manual API token pasting.
- **Asynchronous Event Bus**: Decoupled, non-blocking communication between UIs, connectors, voice loop, engine, and tools.
- **User-Isolated Storage**: All credentials, tokens, and configs reside safely in the user's home directory (`~/.jarvis/`).
