# Creating Custom Tools

## Quick Start

1. Create a new file in the appropriate category under `src/jarvis/tools/`:
   - `basic/` — General-purpose tools
   - `filesystem/` — File operations
   - `system/` — System-level tools
   - `code/` — Code-related tools

2. Subclass `BaseTool` and define a schema:

```python
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

class MyTool(BaseTool):
    schema = ToolSchema(
        name="my_tool",
        description="What this tool does",
        category="basic",
        parameters=[
            ToolParameter(
                name="input",
                type="string",
                description="Input for the tool",
            ),
        ],
        dangerous=False,  # Set True if tool modifies system state
    )

    async def execute(self, **kwargs) -> str:
        input_val = kwargs["input"]
        # ... your logic here ...
        return f"Result: {input_val}"
```

3. The tool will be **auto-discovered** by the registry. No manual registration needed!

## Schema Parameters

- `name`: Unique tool name (used in LLM function calling)
- `description`: What the tool does (shown to the LLM)
- `category`: Tool category (basic, filesystem, system, code)
- `parameters`: List of `ToolParameter` definitions
- `dangerous`: If True, requires user confirmation before execution
