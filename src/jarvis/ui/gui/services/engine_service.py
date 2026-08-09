"""Async engine query service bridging JarvisEngine and PySide6 Qt main thread."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from jarvis.ui.gui.services.dummy_service import DummyAIService

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class _WorkerSignals(QObject):
    response_ready = Signal(str)


class JarvisAIService(QObject):
    """AI Service implementation executing LLM queries on JarvisEngine in background thread."""

    def __init__(self, engine: JarvisEngine | None = None, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.dummy_service = DummyAIService(parent=self)

    def request(self, prompt: str, callback: Callable[[str], None]) -> None:
        if not self.engine:
            self.dummy_service.request(prompt, callback)
            return

        signals = _WorkerSignals()
        signals.response_ready.connect(callback)

        def _run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                chunks: list[str] = []
                async def _collect():
                    async for chunk in self.engine.stream_chat(prompt):  # type: ignore[union-attr]
                        if chunk:
                            chunks.append(chunk)

                loop.run_until_complete(_collect())
                full_text = "".join(chunks).strip()
                if not full_text:
                    full_text = "I received no response from the model."
                signals.response_ready.emit(full_text)
            except Exception as e:
                logger.exception("Error executing JarvisEngine query")
                signals.response_ready.emit(f"Error querying JARVIS engine: {e}")

        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()
