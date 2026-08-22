"""
Connector Discovery — finds messaging bridges on the filesystem.

A connector is any subpackage of ``jarvis.connectors`` (or of the user's
``~/.jarvis/connectors``) that contains a ``connector.py`` defining a concrete
:class:`~jarvis.connectors.base.BaseConnector` subclass. Dropping in a new
folder is enough to register it — nothing has to be added to a hardcoded list.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path

from jarvis.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# Built-in connector packages live next to this module.
BUILTIN_CONNECTORS_DIR = Path(__file__).resolve().parent

# Subpackages of ``jarvis.connectors`` that are infrastructure, not bridges.
_NON_CONNECTOR_DIRS = frozenset({"commands"})

_MODULE_FILENAME = "connector.py"


def get_user_connectors_dir() -> Path:
    """Directory for user-supplied connector packages (~/.jarvis/connectors)."""
    from jarvis.core.paths import get_jarvis_home

    return get_jarvis_home() / "connectors"


def default_search_paths() -> list[Path]:
    """Default discovery locations: built-in connectors, then user connectors."""
    return [BUILTIN_CONNECTORS_DIR, get_user_connectors_dir()]


def _is_connector_package(entry: Path) -> bool:
    """Return True if a directory looks like a connector package."""
    return (
        entry.is_dir()
        and not entry.name.startswith((".", "_"))
        and entry.name not in _NON_CONNECTOR_DIRS
        and (entry / _MODULE_FILENAME).is_file()
    )


def _connector_classes_in(module: object) -> list[type[BaseConnector]]:
    """Extract concrete BaseConnector subclasses defined in a module."""
    found: list[type[BaseConnector]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(obj, BaseConnector)
            and obj is not BaseConnector
            and not inspect.isabstract(obj)
            and obj.__module__ == getattr(module, "__name__", "")
        ):
            found.append(obj)
    return found


def _import_builtin(package_name: str) -> object | None:
    """Import ``jarvis.connectors.<name>.connector`` as a normal module."""
    dotted = f"jarvis.connectors.{package_name}.{Path(_MODULE_FILENAME).stem}"
    try:
        return importlib.import_module(dotted)
    except Exception as e:
        logger.warning("Skipping connector '%s': %s", package_name, e)
        return None


def _import_external(entry: Path) -> object | None:
    """Import a connector module from an arbitrary directory by file path."""
    module_path = entry / _MODULE_FILENAME
    dotted = f"jarvis_user_connectors.{entry.name}.connector"

    existing = sys.modules.get(dotted)
    if existing is not None:
        return existing

    try:
        spec = importlib.util.spec_from_file_location(dotted, module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        sys.modules.pop(dotted, None)
        logger.warning("Skipping user connector at %s: %s", entry, e)
        return None


def discover_connector_classes(
    search_paths: list[Path] | None = None,
) -> dict[str, type[BaseConnector]]:
    """Discover all available connector classes.

    Args:
        search_paths: Directories to scan. Defaults to the built-in connectors
            directory followed by ``~/.jarvis/connectors``.

    Returns:
        Mapping of lowercased connector name to its class. Earlier search paths
        win, so a built-in connector is never shadowed by a user package of the
        same name.
    """
    if search_paths is None:
        search_paths = default_search_paths()

    discovered: dict[str, type[BaseConnector]] = {}

    for search_path in search_paths:
        if not search_path.is_dir():
            continue

        is_builtin = search_path.resolve() == BUILTIN_CONNECTORS_DIR
        for entry in sorted(search_path.iterdir()):
            if not _is_connector_package(entry):
                continue

            module = (
                _import_builtin(entry.name) if is_builtin else _import_external(entry)
            )
            if module is None:
                continue

            for cls in _connector_classes_in(module):
                key = str(getattr(cls, "name", "") or cls.__name__).lower()
                if key in discovered:
                    logger.debug(
                        "Connector '%s' already discovered; ignoring %s", key, cls
                    )
                    continue
                discovered[key] = cls
                logger.debug("Discovered connector '%s' (%s)", key, cls.__name__)

    return discovered
