"""GUI Application runner and lifecycle entry points."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from jarvis.ui.base import BaseUI
from jarvis.ui.gui.windows import JarvisWindow

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


def create_application(argv: list[str] | None = None) -> QApplication:
    """Instantiate or retrieve single QApplication instance."""
    existing = QApplication.instance()
    if existing is not None:
        return existing  # type: ignore[return-value]

    QCoreApplication.setOrganizationName("JARVIS")
    QCoreApplication.setApplicationName("GUI")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
    app.setPalette(palette)
    return app


def main(argv: list[str] | None = None, engine=None) -> int:
    """Launch the main PySide6 application window."""
    app = create_application(argv)
    window = JarvisWindow(engine=engine)
    window.show()
    return app.exec()


class GUIUI(BaseUI):
    """GUI Interface implementation extending BaseUI."""

    async def start(self) -> None:
        logger.info("Launching Desktop GUI...")
        main()

    async def stop(self) -> None:
        pass


async def run_gui(config: JarvisConfig | None = None) -> None:
    """Initialize JarvisEngine and run Desktop GUI."""
    from jarvis.core.engine import JarvisEngine

    logger.info("Starting JARVIS GUI...")
    engine = JarvisEngine()
    try:
        if config:
            await engine.initialize(config)
        main(engine=engine)
    except Exception as e:
        logger.exception("Error initializing JARVIS engine for GUI")
        main()
    finally:
        await engine.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
