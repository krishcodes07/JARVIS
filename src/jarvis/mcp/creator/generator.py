"""
MCP Server Generator — Create new MCP server scaffolding.

Generates a complete, runnable MCP server package (following the platform
package convention) from a name, description, and list of tool definitions.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "servers" / "_template"
SERVERS_DIR = Path(__file__).resolve().parents[1] / "servers"

_PY_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}


class MCPGenerator:
    """Generates MCP server scaffolding."""

    async def generate(
        self,
        name: str,
        description: str,
        tools: list[dict[str, Any]],
        output_dir: Path | None = None,
        author: str = "JARVIS",
        category: str = "custom",
        required_env_vars: list[str] | None = None,
    ) -> Path:
        """Generate a new MCP server package.

        Args:
            name: Server name (e.g., "notion", "slack"). Must be a valid
                Python identifier (lowercase, underscores allowed).
            description: What the server does.
            tools: List of tool definitions with ``name`` and ``description``
                keys (optional ``parameters`` JSON schema).
            output_dir: Where to create the server.
                Defaults to ``servers/<name>``.
            author: Manifest author.
            category: Manifest category.
            required_env_vars: Environment variables the server requires.

        Returns:
            Path to the generated server directory.

        Raises:
            ValueError: If ``name`` is not a valid identifier or the target
                directory already exists.
        """
        if not name.isidentifier() or name.startswith("_"):
            raise ValueError(
                f"Invalid server name '{name}': must be a valid Python identifier."
            )

        target = output_dir or (SERVERS_DIR / name)
        if target.exists():
            raise ValueError(f"Server directory already exists: {target}")

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(TEMPLATE_DIR, target)

        self._write_manifest(
            target,
            name=name,
            description=description,
            author=author,
            category=category,
            required_env_vars=required_env_vars or [],
        )
        self._write_tools(target, name, tools)
        self._cleanup_examples(target)

        logger.info("Generated MCP server '%s' at %s", name, target)
        return target

    # ─── Internal helpers ─────────────────────────────────────

    def _write_manifest(
        self,
        target: Path,
        *,
        name: str,
        description: str,
        author: str,
        category: str,
        required_env_vars: list[str],
    ) -> None:
        env_list = ", ".join(repr(v) for v in required_env_vars)
        source = (
            f'"""Manifest for the "{name}" MCP server."""\n\n'
            "from jarvis.mcp.platform.models import ServerManifest\n\n"
            "MANIFEST = ServerManifest(\n"
            f"    name={name!r},\n"
            '    version="1.0.0",\n'
            f"    description={description!r},\n"
            f"    author={author!r},\n"
            '    homepage="",\n'
            f"    required_env_vars=[{env_list}],\n"
            '    capabilities=["tools", "resources", "prompts"],\n'
            "    dependencies=[],\n"
            "    enabled_by_default=True,\n"
            f"    category={category!r},\n"
            ")\n"
        )
        (target / "manifest.py").write_text(source, encoding="utf-8")

    def _write_tools(self, target: Path, server_name: str, tools: list[dict[str, Any]]) -> None:
        tools_dir = target / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        # Write a module-level __init__ so the package imports cleanly.
        (tools_dir / "__init__.py").write_text("", encoding="utf-8")

        for i, tool in enumerate(tools):
            tool_name = tool.get("name", f"tool_{i}")
            if not tool_name.isidentifier():
                raise ValueError(f"Invalid tool name '{tool_name}' in tool definition #{i}.")

            tool_description = tool.get("description", "")
            params = tool.get("parameters") or {}
            file_path = tools_dir / f"{tool_name}.py"
            file_path.write_text(
                self._render_tool(tool_name, tool_description, params),
                encoding="utf-8",
            )
            logger.debug("Generated tool '%s' -> %s", tool_name, file_path)

    def _render_tool(self, name: str, description: str, params: dict[str, Any]) -> str:
        """Render a single tool module source from a JSON schema definition."""
        properties = params.get("properties", {}) if isinstance(params, dict) else {}
        required = set(params.get("required", [])) if isinstance(params, dict) else set()

        lines: list[str] = [
            '"""',
            f"Tool: {name}",
            f"{description}",
            '"""',
            "",
            "from __future__ import annotations",
            "",
            f'NAME = "{name}"',
            f"DESCRIPTION = {description!r}",
            "",
            "",
            f"def {name}(",
        ]

        args: list[str] = []
        body_parts: list[str] = []
        if properties:
            for pname, spec in properties.items():
                ptype = _PY_TYPE_MAP.get(spec.get("type", "string"), "Any")
                if pname in required:
                    args.append(f"    {pname}: {ptype},")
                else:
                    args.append(f"    {pname}: {ptype} = None,")
                body_parts.append(f"        {pname!r}: {pname},")
            lines.extend(args)
            lines.append(") -> str:")
            lines.extend(
                [
                    '    """',
                    f"    {description or f'{name} tool.'}",
                    '    """',
                    "    try:",
                    "        payload = {",
                ]
            )
            lines.extend(body_parts)
            lines.extend(
                [
                    "        }",
                    f'        return f"Executed {name} with arguments: {{payload}}"',
                    "    except Exception as e:",
                    f'        return f"Error executing {name}: {{e}}"',
                ]
            )
        else:
            lines.append(") -> str:")
            lines.extend(
                [
                    '    """',
                    f"    {description or f'{name} tool.'}",
                    '    """',
                    "    try:",
                    f'        return f"Executed {name} successfully."',
                    "    except Exception as e:",
                    f'        return f"Error executing {name}: {{e}}"',
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def _cleanup_examples(self, target: Path) -> None:
        """Remove the template's example tool/resource/prompt files."""
        for rel in (
            "tools/example_tool.py",
            "resources/example_resource.py",
            "prompts/example_prompt.py",
        ):
            file_path = target / rel
            if file_path.exists():
                file_path.unlink()
        for sub in ("resources", "prompts"):
            init = target / sub / "__init__.py"
            if not init.exists():
                init.parent.mkdir(parents=True, exist_ok=True)
                init.write_text("", encoding="utf-8")
