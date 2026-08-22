# Discovering & Connecting MCP Servers

JARVIS supports **Marketplace Discovery** (finding servers on [mcpmarket.com](https://mcpmarket.com/)), **Terminal UI Connection (`Ctrl+A`)**, and **Dynamic Tool Installation**.

---

## 1. Finding & Installing via JARVIS (`find-mcp`)

You can ask JARVIS to search for and connect any MCP server in natural language:

> *"Find an MCP server for PostgreSQL on mcpmarket and connect it."*
> *"Search for a GitHub MCP server and add my token."*

JARVIS will:
1. Search **mcpmarket.com** and registries via `find_mcp`.
2. Inspect required environment variables and API keys.
3. Prompt you if credentials are required.
4. Persist the configuration in `~/.jarvis/mcp/servers.json` and connect immediately.

---

## 2. Interactive Terminal UI (`Ctrl+A`)

In the TUI MCP modal (`Ctrl+P` or `/mcp`):
1. Press **`Ctrl+A`** (or select **✚ Connect New MCP Server**).
2. Enter the server name, command (e.g. `npx`, `uvx`, `python`), arguments, and optional environment variables.
3. Click **Connect & Save** — the server connects immediately, persists to `~/.jarvis/mcp/servers.json`, and registers all tools.

---

## 3. Creating Custom Python FastMCP Servers

You can build custom MCP servers using Python and the official `mcp` SDK or `FastMCP`:

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my_custom_service")

@mcp.tool()
def calculate_metrics(metric_name: str, value: float) -> str:
    """Calculate and log custom service metrics."""
    return f"Metric {metric_name} computed: {value * 1.5}"

if __name__ == "__main__":
    mcp.run()
```

---

## 4. Registering Custom Servers in `servers.json`

Add your server definition to `~/.jarvis/mcp/servers.json`:

```json
{
  "mcpServers": {
    "my_custom_service": {
      "command": "python",
      "args": ["path/to/server.py"],
      "transport": "stdio",
      "description": "My custom FastMCP service",
      "enabled": true,
      "env": {
        "CUSTOM_KEY": "your_api_key"
      }
    }
  }
}
```

