"""
JARVIS Entry Point — `python -m jarvis` support.

Parses CLI arguments and launches the appropriate UI.
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS — The Ultimate AI Assistant",
    )
    parser.add_argument(
        "--ui",
        choices=["tui", "web", "gui"],
        default=None,
        help="User interface to launch (default: from config)",
    )
    parser.add_argument(
        "--connector",
        choices=["telegram", "discord", "all"],
        default=None,
        help="Run messaging connector bridge in standalone service mode (e.g. telegram, all)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to jarvis.yaml config file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def _get_version() -> str:
    """Get the current JARVIS version."""
    try:
        from jarvis import __version__
        return __version__
    except ImportError:
        return "0.1.0"


async def _run(args: argparse.Namespace) -> None:
    """Main async entry point."""
    from jarvis.core.config import JarvisConfig
    from jarvis.core.logger import setup_logging

    # Load config
    config_path = args.config
    if config_path:
        from pathlib import Path
        config = JarvisConfig.load(Path(config_path))
    else:
        config = JarvisConfig.load()

    # Setup logging
    log_level = "DEBUG" if args.debug else config.jarvis.log_level
    setup_logging(level=log_level)

    # Launch standalone connector if requested
    if args.connector:
        from jarvis.connectors.runner import run_connector_service
        await run_connector_service(config, connector_name=args.connector)
        return

    # Determine UI
    ui_type = args.ui or config.ui.default

    # Launch the appropriate UI
    if ui_type == "tui":
        from jarvis.ui.tui.app import run_tui
        await run_tui(config)
    elif ui_type == "web":
        from jarvis.ui.web.server import run_web
        await run_web(config)
    elif ui_type == "gui":
        from jarvis.ui.gui.app import run_gui
        await run_gui(config)
    else:
        print(f"Unknown UI type: {ui_type}")
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nGoodbye, sir.")
        sys.exit(0)


if __name__ == "__main__":
    main()
