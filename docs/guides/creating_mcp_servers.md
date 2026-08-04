# Creating MCP Servers

## Structure

Each MCP server lives in `src/jarvis/mcp/servers/<name>/`:

```
your_server/
├── __init__.py
├── server.py         # MCP server entry point
├── tools/            # Tool implementations
│   ├── __init__.py
│   └── your_tool.py
└── resources/        # Static resources
```

## Registering

Add your server to `src/jarvis/mcp/servers.json`:

```json
"your_server": {
    "command": "python",
    "args": ["-m", "jarvis.mcp.servers.your_server.server"],
    "transport": "stdio",
    "description": "What your server does",
    "enabled": true
}
```

## Using the Template

Copy `src/jarvis/mcp/servers/_template/` and customize it for your integration.
