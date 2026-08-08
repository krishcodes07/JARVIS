"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from jarvis_gui.main_window import JarvisWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing

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


def main(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    window = JarvisWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

