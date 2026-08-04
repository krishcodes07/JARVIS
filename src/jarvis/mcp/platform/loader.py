"""
Dynamic package and component loader for MCP server packages.

Loads tools, resources, prompts, and configurations from server subdirectories
without hardcoded imports. Every ``*.py`` file in ``tools/``, ``resources/``,
and ``prompts/`` is discovered automatically using a well-defined convention:

- ``tools/<name>.py``      -> exposes ``NAME``, ``DESCRIPTION``, and a
  ``handler()`` (or any public function)
- ``resources/<name>.py``  -> exposes ``URI``, ``NAME``, ``DESCRIPTION``,
  ``MIME_TYPE``, ``loader()``
- ``prompts/<name>.py``    -> exposes ``NAME``, ``DESCRIPTION``, ``TEMPLATE``,
  ``ARGUMENTS``, ``get_prompt()``
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any

from jarvis.mcp.platform.manifest import load_manifest_from_directory
from jarvis.mcp.platform.models import (
    RegisteredPrompt,
    RegisteredPromptArgument,
    RegisteredResource,
    RegisteredTool,
    ServerManifest,
)

logger = logging.getLogger(__name__)

# Package root of the built-in server packages (jarvis.mcp.servers.<name>).
_SERVERS_PACKAGE = "jarvis.mcp.servers"


def _import_module_from_file(module_name: str, file_path: Path) -> Any | None:
    """Import a module by package dot notation, falling back to direct file loading."""
    try:
        return importlib.import_module(module_name)
    except Exception:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


class ServerPackageLoader:
    """Dynamically loads all components from an MCP server directory."""

    def __init__(self, server_dir: Path, servers_package: str = _SERVERS_PACKAGE) -> None:
        self.server_dir = server_dir.resolve()
        self.server_name = self.server_dir.name
        self.servers_package = servers_package
        self.manifest: ServerManifest = (
            load_manifest_from_directory(self.server_dir)
            or ServerManifest(name=self.server_name)
        )

    # ─── Component module helpers ─────────────────────────────

    def _module_name(self, component: str, stem: str) -> str:
        """Build the importable module name for a component file."""
        return f"{self.servers_package}.{self.server_name}.{component}.{stem}"

    def _load_component(self, component: str, stem: str) -> Any | None:
        """Import a component module (tools/resources/prompts)."""
        comp_dir = self.server_dir / component
        file_path = comp_dir / f"{stem}.py"
        return _import_module_from_file(self._module_name(component, stem), file_path)

    # ─── Config ───────────────────────────────────────────────

    def load_config_module(self) -> tuple[dict[str, Any], list[str]]:
        """Load ``config.py`` from the server directory.

        Returns:
            Tuple of (config_dict, validation_errors).
        """
        config_file = self.server_dir / "config.py"
        if not config_file.exists():
            return {}, []

        try:
            mod = _import_module_from_file(
                f"{self.servers_package}.{self.server_name}.config", config_file
            )
            if not mod:
                return {}, []

            errors: list[str] = []
            if hasattr(mod, "validate") and callable(mod.validate):
                errors = list(mod.validate())

            config_dict: dict[str, Any] = {}
            if hasattr(mod, "CONFIG"):
                config_dict = mod.CONFIG
            elif hasattr(mod, "get_config") and callable(mod.get_config):
                config_dict = mod.get_config()

            return config_dict, errors
        except Exception as e:
            logger.error("Error loading config for %s: %s", self.server_name, e)
            return {}, [str(e)]

    # ─── Tools ────────────────────────────────────────────────

    def discover_tools(self) -> list[RegisteredTool]:
        """Discover all tool functions from the server's ``tools/`` directory."""
        tools_dir = self.server_dir / "tools"
        tools: list[RegisteredTool] = []

        if not tools_dir.exists() or not tools_dir.is_dir():
            return tools

        for file_path in sorted(tools_dir.glob("*.py")):
            if file_path.name.startswith(("_", ".")):
                continue

            try:
                mod = self._load_component("tools", file_path.stem)
                if not mod:
                    continue

                tool_func = None
                tool_name = file_path.stem

                if hasattr(mod, "handler") and callable(mod.handler):
                    tool_func = mod.handler
                elif hasattr(mod, tool_name) and callable(getattr(mod, tool_name)):
                    tool_func = getattr(mod, tool_name)
                else:
                    for name, obj in inspect.getmembers(mod, inspect.isfunction):
                        if not name.startswith("_") and obj.__module__ == mod.__name__:
                            tool_func = obj
                            tool_name = name
                            break

                if tool_func:
                    tool_name = getattr(mod, "NAME", tool_name)
                    tool_desc = getattr(mod, "DESCRIPTION", tool_func.__doc__ or "").strip()
                    tools.append(
                        RegisteredTool(
                            name=tool_name,
                            qualified_name=f"{self.server_name}__{tool_name}",
                            description=tool_desc,
                            server_name=self.server_name,
                            func=tool_func,
                        )
                    )
            except Exception as e:
                logger.error("Error loading tool from %s: %s", file_path, e)

        return tools

    # ─── Resources ────────────────────────────────────────────

    def discover_resources(self) -> list[RegisteredResource]:
        """Discover all resource definitions from the server's ``resources/`` directory."""
        resources_dir = self.server_dir / "resources"
        resources: list[RegisteredResource] = []

        if not resources_dir.exists() or not resources_dir.is_dir():
            return resources

        for file_path in sorted(resources_dir.glob("*.py")):
            if file_path.name.startswith(("_", ".")):
                continue

            try:
                mod = self._load_component("resources", file_path.stem)
                if not mod:
                    continue

                uri = getattr(mod, "URI", f"{self.server_name}://{file_path.stem}")
                name = getattr(mod, "NAME", file_path.stem.replace("_", " ").title())
                description = getattr(mod, "DESCRIPTION", mod.__doc__ or "").strip()
                mime_type = getattr(mod, "MIME_TYPE", "text/plain")

                loader_func = None
                if hasattr(mod, "loader") and callable(mod.loader):
                    loader_func = mod.loader
                elif hasattr(mod, "read_resource") and callable(mod.read_resource):
                    loader_func = mod.read_resource
                elif hasattr(mod, file_path.stem) and callable(getattr(mod, file_path.stem)):
                    loader_func = getattr(mod, file_path.stem)
                else:
                    for n, obj in inspect.getmembers(mod, inspect.isfunction):
                        if not n.startswith("_") and obj.__module__ == mod.__name__:
                            loader_func = obj
                            break

                resources.append(
                    RegisteredResource(
                        uri=uri,
                        name=name,
                        description=description,
                        server_name=self.server_name,
                        mime_type=mime_type,
                        func=loader_func,
                    )
                )
            except Exception as e:
                logger.error("Error loading resource from %s: %s", file_path, e)

        return resources

    # ─── Prompts ──────────────────────────────────────────────

    def discover_prompts(self) -> list[RegisteredPrompt]:
        """Discover all prompt definitions from the server's ``prompts/`` directory."""
        prompts_dir = self.server_dir / "prompts"
        prompts: list[RegisteredPrompt] = []

        if not prompts_dir.exists() or not prompts_dir.is_dir():
            return prompts

        for file_path in sorted(prompts_dir.glob("*.py")):
            if file_path.name.startswith(("_", ".")):
                continue

            try:
                mod = self._load_component("prompts", file_path.stem)
                if not mod:
                    continue

                name = getattr(mod, "NAME", file_path.stem.replace("_", " ").title())
                description = getattr(mod, "DESCRIPTION", mod.__doc__ or "").strip()
                template = getattr(mod, "TEMPLATE", "")

                arguments: list[RegisteredPromptArgument] = []
                for arg in getattr(mod, "ARGUMENTS", []):
                    if isinstance(arg, dict):
                        arguments.append(RegisteredPromptArgument(**arg))
                    elif isinstance(arg, RegisteredPromptArgument):
                        arguments.append(arg)

                func = None
                if hasattr(mod, "get_prompt") and callable(mod.get_prompt):
                    func = mod.get_prompt
                elif hasattr(mod, "template_func") and callable(mod.template_func):
                    func = mod.template_func

                prompts.append(
                    RegisteredPrompt(
                        name=name,
                        description=description,
                        server_name=self.server_name,
                        template=template,
                        arguments=arguments,
                        func=func,
                    )
                )
            except Exception as e:
                logger.error("Error loading prompt from %s: %s", file_path, e)

        return prompts
