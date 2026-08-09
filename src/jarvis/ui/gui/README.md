# JARVIS GUI

A reusable PySide6 desktop UI inspired by the supplied JARVIS concept. The glowing
orb is drawn and animated at runtime, so its appearance is not tied to a static
image. Themes, accent colors, animation speed, wave strength, and particle density
can all be changed from the Settings drawer.

## Features

- Responsive, frameless-style dark interface that scales down to 900 x 600
- Animated `JarvisOrb` rendered with `QPainter`
- Dedicated settings page with theme and visualizer controls
- Collapsible navigation drawer and reusable painted icon buttons
- Functional prompt bar with attach, microphone, send, and Enter-to-send actions
- ChatGPT-style local conversation history with full message transcripts
- SQLite persistence and recent-chat reopening from the navigation drawer
- Asynchronous dummy AI service that can later be replaced by the real JARVIS backend
- Settings persistence with `QSettings`

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python run.py
```

Or install the project in editable mode and use the console command:

```powershell
python -m pip install -e .
jarvis-gui
```

## Project layout

```text
src/jarvis_gui/
  app.py                 application entry point
  config.py              persisted UI preferences
  conversation_store.py  SQLite conversations and messages
  dummy_ai.py            replaceable response service
  themes.py              theme tokens and stylesheet builder
  main_window.py         application composition
  components/            reusable Qt widgets
tests/                   smoke and behavior tests
```

## Connecting the real assistant

Implement the same `request(prompt, callback)` shape as `DummyAIService`, then pass
that service to `JarvisWindow(ai_service=...)`. Keeping this boundary separate means
the UI does not need to know whether a reply comes from a local model, API, or the
existing JARVIS project.

Conversation history is stored in the operating system's application-data folder
as `conversations.db`, keeping runtime data outside the source repository.
