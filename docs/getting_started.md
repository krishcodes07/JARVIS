# Getting Started with JARVIS

## Prerequisites

- **Python 3.11.4+**
- An API key for at least one supported LLM provider (Groq, OpenAI, Anthropic, Google Gemini, NVIDIA NIM, OpenRouter, OpenCode Zen, TokenRouter, etc.)

> [!IMPORTANT]
> **Interface Status**: Currently, **only the Terminal UI (`tui`)** is active and under active development. The Web UI (`web`) and Desktop GUI (`gui`) options are in early development and not functional yet.

---

## Installation

### Option A: Automated First-Time Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/krishcodes07/JARVIS.git
cd JARVIS

# Run the interactive setup script
python scripts/setup.py
```

### Option B: Manual Setup

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

# Copy environment variable template
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac
```

### Optional Extras Installation

Depending on your requirements, you can install additional capability modules:

```bash
# Voice suite (TTS streaming, STT input, faster-whisper)
pip install -e ".[voice]"

# MCP server extras (Excel spreadsheet parsing, Telegram client)
pip install -e ".[mcp]"

# Development, testing, and linting suite (pytest, ruff, mypy)
pip install -e ".[dev]"

# Install all optional dependencies
pip install -e ".[voice,mcp,dev]"
```

---

## Quick Configuration

### 1. Set API Keys

Edit `.env` and fill in credentials for your active providers:

```env
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=sk-your_key_here
```

### 2. Choose Your Active Provider

Edit `config/jarvis.yaml` to specify your preferred backend:

```yaml
provider:
  active: "groq"
  model: "llama-3.3-70b-versatile"
```

---

## Launching JARVIS

Start JARVIS using the active Terminal UI:

```bash
# Terminal UI (Default active interface)
python main.py

# Launch with Debug Logging enabled
python main.py --debug
```

---

## Documentation & Next Steps

- Explore the [System Architecture](architecture.md)
- Learn full [Configuration Reference](configuration.md)
- Learn how to [Add New Providers](guides/adding_providers.md)
- Learn how to [Create Custom Tools](guides/creating_tools.md)
- Learn how to [Create MCP Servers](guides/creating_mcp_servers.md)
- Review [Contributing Guidelines](../CONTRIBUTING.md)
