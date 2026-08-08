"""
TUI App — Terminal User Interface for JARVIS.

Built with Textual for high-performance terminal UI rendering, OpenCode-styled
prompt box, modal command palettes, model selection, session management,
and real-time streaming LLM responses.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import TYPE_CHECKING, Any

from textual.app import App

from jarvis.ui.tui.screens.main_screen import MainScreen
from jarvis.ui.tui.theme import JARVIS_CSS

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


def patch_textual_mouse_driver() -> None:
    """Enable standard mouse support in Textual."""
    pass


class JarvisTUIApp(App):
    """Textual Terminal User Interface App for JARVIS."""

    TITLE = "JARVIS AI Assistant"
    SUB_TITLE = "Just A Rather Very Intelligent System"
    CSS = JARVIS_CSS

    def __init__(self, engine: JarvisEngine | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.engine = engine

    def on_mount(self) -> None:
        with contextlib.suppress(Exception):
            sys.stdout.write("\x1b[?1003l")
            sys.stdout.flush()

        from jarvis.ui.tui.theme import apply_theme, register_all_themes

        register_all_themes(self)
        if self.engine and self.engine.config and self.engine.config.ui:
            active_theme = self.engine.config.ui.tui.theme
            apply_theme(self, active_theme)
        else:
            apply_theme(self, "jarvis")
        self.push_screen(MainScreen(engine=self.engine))


async def run_tui(config: JarvisConfig) -> None:
    """Launch the interactive JARVIS Terminal UI.

    Args:
        config: JARVIS configuration object.
    """
    from jarvis.core.engine import JarvisEngine

    logger.info("Starting JARVIS TUI...")
    engine = JarvisEngine()

    try:
        await engine.initialize(config)
        app = JarvisTUIApp(engine=engine)
        await app.run_async()
    except Exception as e:
        logger.exception("Failed running JARVIS TUI app")
        print(f"Error launching TUI: {e}")
    finally:
        await engine.shutdown()
