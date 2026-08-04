"""
MCP Installer — Install MCP servers from npm, pip, or Git.

Installing an MCP server makes it available to JARVIS by registering its
launch configuration (command, args, transport, env) in the MCP registry so
it is persisted and started with the rest of the fleet.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from jarvis.core.exceptions import MCPError

logger = logging.getLogger(__name__)

SERVERS_DIR = Path(__file__).resolve().parent / "servers"


class MCPInstaller:
    """Installs MCP servers from various sources.

    Supports:
    - npm packages (launched via ``npx -y``)
    - pip packages (installed with pip, launched as a module)
    - Git repositories (cloned into the local servers directory)
    """

    async def install_from_npm(
        self,
        package_name: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        server_name: str | None = None,
    ) -> dict[str, Any]:
        """Install an MCP server from npm.

        Args:
            package_name: npm package name (e.g. ``@modelcontextprotocol/server-everything``).
            args: Additional CLI args passed to the server at launch.
            env: Environment variables required by the server.
            server_name: Optional override for the registered server name.

        Returns:
            The registered server config.

        Raises:
            MCPError: If npx is unavailable.
        """
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        if not npx:
            raise MCPError("npx not found on PATH. Install Node.js to use npm servers.")

        name = server_name or _derive_name(package_name)
        config = {
            "command": npx,
            "args": ["-y", package_name, *(args or [])],
            "transport": "stdio",
            "description": f"npm MCP server: {package_name}",
            "enabled": True,
            "env": env or {},
        }
        return await self._finalize(name, config)

    async def install_from_pip(
        self,
        package_name: str,
        module: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        server_name: str | None = None,
    ) -> dict[str, Any]:
        """Install an MCP server from pip.

        Args:
            package_name: pip distribution name.
            module: Python module to run (defaults to ``<package_name>.server``).
            args: Additional CLI args passed to the server at launch.
            env: Environment variables required by the server.
            server_name: Optional override for the registered server name.

        Returns:
            The registered server config.

        Raises:
            MCPError: If pip install fails.
        """
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            package_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise MCPError(
                f"pip install '{package_name}' failed: {stderr.decode(errors='replace')}"
            )

        name = server_name or _derive_name(package_name)
        config = {
            "command": sys.executable,
            "args": ["-m", module or f"{package_name}.server", *(args or [])],
            "transport": "stdio",
            "description": f"pip MCP server: {package_name}",
            "enabled": True,
            "env": env or {},
        }
        return await self._finalize(name, config)

    async def install_from_git(
        self,
        repo_url: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        server_name: str | None = None,
    ) -> dict[str, Any]:
        """Install an MCP server from a Git repository.

        Clones the repository into ``servers/<name>`` and registers it,
        assuming it follows the JARVIS server package convention
        (``server.py`` entrypoint + ``manifest.py``).

        Args:
            repo_url: Git clone URL.
            args: Additional CLI args passed to the server at launch.
            env: Environment variables required by the server.
            server_name: Optional override for the registered server name.

        Returns:
            The registered server config.

        Raises:
            MCPError: If git is unavailable or the clone fails.
        """
        git = shutil.which("git")
        if not git:
            raise MCPError("git not found on PATH.")

        name = server_name or _derive_repo_name(repo_url)
        target = SERVERS_DIR / name
        if target.exists():
            raise MCPError(f"Server directory already exists: {target}")

        proc = await asyncio.create_subprocess_exec(
            git,
            "clone",
            "--depth",
            "1",
            repo_url,
            str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise MCPError(f"git clone '{repo_url}' failed: {stderr.decode(errors='replace')}")

        server_file = target / "server.py"
        if not server_file.exists():
            raise MCPError(
                f"Cloned repo '{repo_url}' has no 'server.py' entrypoint in {target}."
            )

        config = {
            "command": sys.executable,
            "args": ["-m", f"jarvis.mcp.servers.{name}.server", *(args or [])],
            "transport": "stdio",
            "description": f"git MCP server: {repo_url}",
            "enabled": True,
            "env": env or {},
        }
        return await self._finalize(name, config)

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search for available MCP servers.

        Returns locally registered/known servers matching the query.
        """
        from jarvis.mcp.registry import MCPRegistry

        registry = MCPRegistry()
        registry.load()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        for name, config in registry.get_all().items():
            haystack = f"{name} {config.get('description', '')}".lower()
            if query_lower in haystack:
                results.append({"name": name, "source": "configured", **config})
        return results

    async def _finalize(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        """Register the config in the persistent user-level registry."""
        from jarvis.mcp.registry import MCPRegistry

        registry = MCPRegistry()
        registry.load()
        registry.register(name, config)
        registry.save_user_config()
        logger.info("Registered MCP server '%s' (%s)", name, config.get("description"))
        return {"name": name, **config}


def _derive_name(package_name: str) -> str:
    """Derive a server name from an npm/pip package name."""
    base = package_name.rsplit("/", 1)[-1]
    return base.replace("-", "_").replace(".", "_").lower()


def _derive_repo_name(repo_url: str) -> str:
    """Derive a server name from a git repo URL."""
    base = repo_url.rstrip("/").split("/")[-1]
    if base.endswith(".git"):
        base = base[:-4]
    return base.replace("-", "_").replace(".", "_").lower()
