"""Canned response mock AI service for GUI testing/offline operation."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


class DummyAIService(QObject):
    """Return contextual canned replies without blocking the Qt event loop."""

    def __init__(self, delay_ms: int = 850, parent=None) -> None:
        super().__init__(parent)
        self.delay_ms = delay_ms

    def request(self, prompt: str, callback: Callable[[str], None]) -> None:
        QTimer.singleShot(
            self.delay_ms,
            self,
            lambda: callback(self._build_response(prompt)),
        )

    @staticmethod
    def _build_response(prompt: str) -> str:
        normalized = prompt.casefold()
        if any(word in normalized for word in ("hello", "hey", "hi ")):
            return "Hello. JARVIS interface online and ready for your command."
        if "time" in normalized:
            return "The clock module is still in demo mode. Connect the real tool layer to return live time data."
        if any(word in normalized for word in ("code", "python", "debug")):
            return "I can help with that. This response is running in fallback mode; connect the live JARVIS engine for execution."
        if any(word in normalized for word in ("weather", "temperature")):
            return "Weather tools are available when connected to the live engine service."
        return f'I received: “{prompt}”. The UI is ready and functioning normally.'
