# Contributing to JARVIS

Thank you for your interest in contributing to JARVIS! This guide will help you get started.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/krishcodes07/JARVIS.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Install dependencies**: `pip install -e ".[dev]"`
5. **Make your changes**
6. **Run tests**: `pytest`
7. **Submit a Pull Request**

## Development Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/JARVIS.git
cd JARVIS

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in development mode with all extras
pip install -e ".[voice,mcp,dev]"

# Copy .env template and add your API keys
copy .env.example .env     # Windows
# cp .env.example .env     # Linux/Mac
```

## Project Structure

- `src/jarvis/connectors/` — Messaging platform bridges (Telegram, Discord) and standalone runner
- `src/jarvis/core/` — Core engine, event bus, and hierarchical configuration
- `src/jarvis/mcp/` — MCP (Model Context Protocol) subsystem and servers
- `src/jarvis/memory/` — Short-term, long-term, and vector RAG memory
- `src/jarvis/prompts/` — System prompts and persona definitions
- `src/jarvis/providers/` — LLM provider integrations and protocols (OpenAI, Anthropic, Google Gemini, models.dev)
- `src/jarvis/skills/` — Specialized autonomous skill modules
- `src/jarvis/tools/` — Built-in tools and security sandbox
- `src/jarvis/ui/` — User interfaces (TUI, Web UI, Desktop GUI)
- `src/jarvis/voice/` — Voice synthesis (TTS), recognition (STT), and audio management
- `config/` — Configuration templates
- `tests/` — Test suite

## Code Standards

- **Type hints**: Use type hints for all function signatures
- **Docstrings**: Use Google-style docstrings
- **Formatting**: Follow PEP 8 (we use `ruff` for linting)
- **Tests**: Write tests for new features
- **Commits**: Use conventional commit messages (`feat:`, `fix:`, `docs:`, etc.)

## Adding New Components

### Adding a Provider
See [docs/guides/adding_providers.md](docs/guides/adding_providers.md)

### Creating a Tool
See [docs/guides/creating_tools.md](docs/guides/creating_tools.md)

### Creating an MCP Server
See [docs/guides/creating_mcp_servers.md](docs/guides/creating_mcp_servers.md)

## Questions?

Open an issue or start a discussion — we're happy to help!
