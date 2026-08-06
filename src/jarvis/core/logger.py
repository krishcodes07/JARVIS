"""
JARVIS Logger — Centralized logging setup.

Configures structured logging with Rich formatting for console output
and file rotation for persistent logs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_dir: Path | None = None,
    log_file: str = "jarvis.log",
) -> None:
    """Configure JARVIS logging.

    Sets up:
    - Rich console handler (colorized, structured output)
    - File handler (rotating log file)

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files. Defaults to data/logs/.
        log_file: Name of the log file.
    """
    from jarvis.core.config import DATA_DIR

    if log_dir is None:
        log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger("jarvis")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # ── Console handler (Rich) ──
    console_handler = RichHandler(
        console=Console(stderr=True),
        show_path=False,
        show_time=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter("%(message)s", datefmt="[%X]")
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # ── File handler ──
    file_handler = logging.FileHandler(
        log_dir / log_file,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    root_logger.info(f"Logging initialized at {level} level.")
