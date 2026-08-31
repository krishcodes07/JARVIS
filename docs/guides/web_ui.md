# JARVIS Web UI Guide

The **JARVIS Web UI** is a state-of-the-art, responsive single-page web application (SPA) built with React 18, TypeScript, Tailwind CSS, Framer Motion, and Three.js/ThreeUI WebGL shaders, served by a high-performance FastAPI and WebSocket backend.

---

## Key Features

- **Real-Time Streaming Chat** — Low-latency Server-Sent Events / WebSocket message streaming with full Markdown rendering, code highlighting, copy utilities, interactive task lists, and tables.
- **Collapsible Reasoning Blocks** — Live `<think>` and `<thought>` token parsing with collapsible thought accordions and reasoning effort indicators.
- **Live Tool Execution Pills** — Real-time visualization of tool invocations, arguments, and execution statuses (`running`, `completed`, `error`) with expandable result payloads.
- **Interactive `ask_user` Tool Card** — Allows JARVIS to prompt the user with single/multiple-choice questions or text inputs directly within the chat transcript.
- **Hands-Free Voice Chat Overlay** — Dedicated full-screen voice mode with:
  - Audio-reactive 3D/2D visualizer orb with real-time FFT frequency levels.
  - Browser-native **Real-Time Speech-to-Text (STT)** powered by Web Speech API with live streaming transcript display.
  - Automatic pause/silence detection (auto-stops and sends after you pause speaking).
  - Sentence-level streaming Text-to-Speech (TTS) audio playback with automatic listening resumption.
  - Live status indicator displaying current state (`Listening…`, `Processing…`, `Using <tool_name>…`, `Speaking…`).
- **Rich Procedural Backgrounds & Themes** — 14 curated color themes, 9+ procedural WebGL shader background scenes (powered by ThreeUI), and a customizable background opacity slider.
- **Comprehensive Settings Hub** — Dedicated management dialogs for:
  - **Models & Providers**: Switch across 180+ LLM providers via `models.dev`, manage API keys, and configure reasoning effort.
  - **Appearance**: Themes, Orb renderers, background shaders, and opacity controls.
  - **Voice**: Edge TTS / ElevenLabs voice models, pitch, speech rate, and character budgets.
  - **MCP Servers**: Inspect, add, edit, and restart Model Context Protocol stdio/npx servers.
  - **Messaging Connectors**: Manage Telegram & Discord bot bridge tokens, allowlists, and live uptimes.
  - **Memory Inspector**: Inspect conversation sessions, view long-term memories, and check vector DB health.
  - **Skills Manager**: Enable/disable modular skills (coding, bug-hunting, deep-research, etc.).
  - **Tools Explorer**: Browse all available built-in tools with parameter schemas and auto-approval toggles.
  - **System Status**: Real-time health metrics, engine status, and connector statuses.
- **Session Drawer** — Sidebar conversation list with search, rename, and deletion capabilities.
- **Slash Commands Autocomplete** — Quick `/` trigger popup with live keyboard navigation for `/new`, `/clear`, `/effort`, `/theme`, `/models`, `/mcp`, etc.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        JARVIS Web UI Architecture                      │
├───────────────────────────────────┬────────────────────────────────────┤
│           Frontend (SPA)          │          Backend (FastAPI)         │
│  React 18 + TypeScript + Vite     │  FastAPI + Uvicorn + WebSockets    │
├───────────────────────────────────┼────────────────────────────────────┤
│ • AppShell & Responsive Layout    │ • /ws/chat (WebSocket streaming)   │
│ • JarvisContext (State & WS loop) │ • /api/system (Health & metrics)   │
│ • RealtimeSTT (Web Speech API)    │ • /api/config (Runtime YAML API)   │
│ • AudioService (Worklet / FFT)    │ • /api/sessions (Conversation CRUD)│
│ • VoiceOverlay & JarvisBlob       │ • /api/mcp (MCP server registry)   │
│ • ThreeBackground (WebGL Shaders) │ • /api/skills (Skills registry)    │
│ • MarkdownRenderer (react-markdown) • /api/connectors (Telegram/Discord)│
│ • Settings Modal Dialogs          │ • /api/voice (TTS & transcribe)    │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## Quick Start & Running the Web UI

### 1. Launch with the CLI

Run JARVIS with the `--ui web` flag:

```bash
# Launch JARVIS Web UI (default host 127.0.0.1, port 5000)
python main.py --ui web

# Or run via module invocation
python -m jarvis --ui web
```

Once started, navigate to:
```
http://127.0.0.1:5000/
```

### 2. Custom Host and Port Configuration

You can configure the host and port in `~/.jarvis/config/jarvis.yaml`:

```yaml
ui:
  web:
    host: "127.0.0.1"
    port: 5000
```

---

## Frontend Development & Building

The frontend source code is located in `src/jarvis/ui/web/frontend/`.

### Prerequisites
- **Node.js 18+** and **npm**

### 1. Install Dependencies
```bash
cd src/jarvis/ui/web/frontend
npm install
```

### 2. Development Mode (Hot Module Replacement)
```bash
npm run dev
```
Open `http://localhost:5173/` in your browser. Vite automatically proxies `/api` and `/ws` requests to the FastAPI backend running on port 5000.

### 3. Production Build
```bash
npm run build
```
This compiles and bundles all assets into `src/jarvis/ui/web/frontend/dist/`, which is automatically served by the FastAPI application.

---

## Voice Mode & Audio Architecture

JARVIS Web UI features a real-time hands-free voice overlay accessible by clicking the **Voice Chat** button in the top navigation bar or pressing the microphone trigger.

### Real-Time Streaming STT (`RealtimeSTT`)
- Uses the browser's native `SpeechRecognition` / `webkitSpeechRecognition` API.
- Enables `continuous = true` and `interimResults = true` so spoken words stream into the transcript in real-time.
- Employs a silence pause detection timer (1.2 seconds) that automatically stops recording and dispatches the message as soon as you finish speaking.
- Automatically handles network retries and restarts on timeouts without user intervention.

### Low-Latency TTS Streaming
- Responses from the backend are stripped of raw markdown and reasoning blocks via `stripMarkdownForSpeech`.
- Unspoken sentences are detected in real-time as LLM tokens stream in.
- Completed sentences are dispatched to the `/api/voice/tts` endpoint early, allowing speech audio playback to begin before the model has even finished generating the entire response.
- Once JARVIS finishes speaking, the audio loop automatically re-arms the microphone for the next turn.

### Audio-Reactive Visualizer (`JarvisBlob`)
- Captures microphone audio using `navigator.mediaDevices.getUserMedia` with `AudioContext` and `AnalyserNode` (FFT size 64).
- Computes frequency band energy and animates the 3D/2D blob orb in real time.

---

## Personalization & Visual Customization

### Themes (14 Built-In Presets)
Access the **Settings** $\rightarrow$ **Appearance** panel to choose between themes including:
- **Default Dark / Midnight / Obsidian**
- **Cyberpunk / Matrix / Synthwave**
- **Nordic / Emerald / Sunset / Solar**
- **Light & High-Contrast variants**

Themes dynamically update CSS custom properties for background void colors, surface panels, accent glows, borders, and text tokens.

### Procedural Background Shaders
Choose from procedural WebGL and Canvas backgrounds powered by ThreeUI:
- **Ribbon Field** — Fluid, chromatic 3D ribbons responding to cursor movements.
- **Amber Halftone** — Retro halftone pattern flow with depth attenuation.
- **Void Field** — Deep spatial particle drift.
- **Halftone Flow** — Dynamic waves of geometric halftone grids.
- **Data Pixel Arc** — Curved matrix data stream.
- **Dot Matrix** — Interactive pulsing dot grid.
- **Classic Floor** — Iconic JARVIS perspective grid with horizon glow.

### Background Opacity Control
Use the opacity slider in **Appearance Settings** to adjust background visibility from 10% to 100% with instant live preview.

---

## WebSocket Protocol Specification

The real-time chat connects over `/ws/chat`.

### Client $\rightarrow$ Server Messages

#### Send Message
```json
{
  "type": "message",
  "content": "Hello JARVIS",
  "session_id": "optional-session-id"
}
```

#### Respond to `ask_user` Tool
```json
{
  "type": "ask_user_response",
  "prompt_id": "prompt-1234",
  "answers": {
    "question_0": "User selected option"
  }
}
```

### Server $\rightarrow$ Client Events

| Event Type | Payload Fields | Description |
|---|---|---|
| `start` | `{ model, session_id }` | Generation started for the turn. |
| `content` | `{ content }` | Incremental text chunk from the assistant. |
| `tool_call` | `{ tool, args }` | Tool execution initiated. |
| `tool_result` | `{ tool, result, is_error }` | Tool execution completed. |
| `ask_user` | `{ prompt_id, questions }` | Interactive user prompt request. |
| `done` | `{}` | Generation turn completed. |
| `error` | `{ error }` | Error message during generation. |

---

## REST API Reference

All REST endpoints are mounted under `/api/`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/system/health` | Engine initialization status and subsystem health. |
| `GET` | `/api/system/info` | Application version, OS, and runtime metadata. |
| `GET` | `/api/config` | Retrieve active JARVIS configuration. |
| `PATCH`| `/api/config` | Update active configuration parameters. |
| `GET` | `/api/sessions` | List all conversation sessions. |
| `POST`| `/api/sessions` | Create a new conversation session. |
| `GET` | `/api/sessions/{id}` | Get messages and history for a session. |
| `DELETE`| `/api/sessions/{id}` | Delete a conversation session. |
| `PATCH`| `/api/sessions/{id}` | Rename a conversation session. |
| `GET` | `/api/mcp/servers` | List registered MCP servers and their statuses. |
| `POST`| `/api/mcp/servers` | Add or update an MCP server definition. |
| `DELETE`| `/api/mcp/servers/{name}` | Remove an MCP server. |
| `GET` | `/api/skills` | List all available autonomous skills. |
| `PATCH`| `/api/skills/{name}` | Enable or disable a skill. |
| `GET` | `/api/connectors` | List messaging connectors (Telegram, Discord) and uptimes. |
| `POST`| `/api/connectors/{name}` | Configure connector tokens and allowlists. |
| `GET` | `/api/tools` | List all available tools and their JSON schemas. |
| `POST`| `/api/voice/transcribe` | Transcribe a multipart PCM WAV audio file. |
| `POST`| `/api/voice/tts` | Synthesize text into an audio file (MP3/WAV). |
| `GET` | `/api/voice/voices` | List available TTS voices and providers. |
