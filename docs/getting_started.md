# Getting Started with JARVIS

## Prerequisites

- **Python 3.11.4+**
- An API key for at least one supported LLM provider (Groq, OpenAI, Anthropic, Google Gemini, NVIDIA NIM, OpenRouter, OpenCode Zen, TokenRouter, etc.)

> [!IMPORTANT]
> **Interface Status**: Currently, **only the Terminal UI (`tui`)** is active and under active development. The Web UI (`web`) and Desktop GUI (`gui`) options are in early development and not functional yet.

---

## Installation
 
```bash
# Clone the repository
git clone https://github.com/krishcodes07/JARVIS.git
cd JARVIS

# Create and activate a Python 3.11.4 virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/Mac

# Install JARVIS core package
pip install -e .
```

---

## First-Time Setup Wizard (Recommended)

Run the interactive setup wizard to validate your provider credentials and configure local embeddings:

```bash
python setup.py
# or
python -m jarvis --setup
```

The wizard will:
1. Validate your API keys against live provider endpoints without token cost.
2. Verify model availability and extended thinking support.
3. Test or download the bundled offline embedding model (`all-MiniLM-L6-v2`).
4. Persist your settings to `~/.jarvis/config/jarvis.yaml` and `~/.jarvis/.env`.

---

## Service Authentication (OAuth & Telegram)

Authenticate your personal Google and Telegram accounts directly from the terminal or the in-app MCP modal:

```bash
# Google Account (Gmail & Calendar) via Native Browser OAuth 2.0
python main.py --connect gmail
python main.py --connect calendar

# Personal Telegram User Account (MTProto)
python main.py --connect telegram
```

Tokens are automatically encrypted and saved to `~/.jarvis/auth/tokens.json`.

---

## Manual Configuration (Alternative)

### 1. Set API Keys

Edit `~/.jarvis/.env` (or `.env` in repository root):

```env
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=sk-your_key_here
```

### 2. Choose Your Active Provider

Edit `~/.jarvis/config/jarvis.yaml`:

```yaml
provider:
  active: "groq"
  model: "llama-3.3-70b-versatile"

memory:
  vector:
    enabled: true
    embedding_backend: "auto"     # auto (prefers remote provider, falls back to local MiniLM)
```

---

## Launching JARVIS

### 1. Interactive Terminal UI (Default)

Start JARVIS using the interactive Terminal UI:

```bash
# Terminal UI (Default active interface)
python main.py
# or
python -m jarvis --ui tui

# Launch with Debug Logging enabled
python main.py --debug
```

### 2. Messaging Connector Bridges (Background / Service Mode)

Run JARVIS as a Telegram or Discord bot bridge:

```bash
# Run Telegram bot bridge
python -m jarvis --connector telegram

# Run Discord bot bridge
python -m jarvis --connector discord

# Run all enabled bridges simultaneously
python -m jarvis --connector all
```

---

## Documentation & Next Steps

- Explore the [System Architecture](architecture.md)
- Learn full [Configuration Reference](configuration.md)
- Learn how to [Add New Providers](guides/adding_providers.md)
- Learn how to [Create Custom Tools](guides/creating_tools.md)
- Learn how to [Create MCP Servers](guides/creating_mcp_servers.md)
- Review [Contributing Guidelines](../CONTRIBUTING.md)
