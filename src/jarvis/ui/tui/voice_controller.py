"""
Voice Session Controller for JARVIS TUI.
Decouples voice mode orchestration (STT capture, TTS synthesis, state management) from MainScreen.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.core.engine import JarvisEngine

logger = logging.getLogger(__name__)


class VoiceSessionController:
    """Manages voice mode lifecycle, microphone STT input, and TTS response playback for TUI."""

    def __init__(self, engine: JarvisEngine | None = None) -> None:
        self.engine = engine
        self.is_active: bool = False

    async def ensure_initialized(self) -> tuple[bool, str]:
        """Ensure VoiceManager is instantiated and initialized.

        Returns:
            Tuple of (success_boolean, error_message_if_any).
        """
        if not self.engine:
            return False, "JARVIS engine not connected."

        if not self.engine.voice_manager and self.engine.config:
            from jarvis.voice.manager import VoiceManager

            try:
                manager = VoiceManager(self.engine.config)
                await manager.initialize()
                self.engine.voice_manager = manager
            except Exception as e:
                return False, f"Could not initialize voice manager: {e}"

        vm = self.engine.voice_manager
        if not vm or not getattr(vm, "_initialized", False):
            return False, "Voice subsystem disabled or unavailable (check mic/audio settings)."

        return True, ""

    def stop(self) -> None:
        """Stop active voice session and interrupt audio playback."""
        self.is_active = False
        if self.engine and self.engine.voice_manager:
            self.engine.voice_manager.stop()

    def get_status_info(self) -> dict[str, str | bool]:
        """Get voice subsystem info for UI status display."""
        if not self.engine or not self.engine.voice_manager:
            return {
                "active": False,
                "stt_provider": "disabled",
                "tts_provider": "disabled",
                "initialized": False,
            }

        vm = self.engine.voice_manager
        return {
            "active": self.is_active,
            "stt_provider": str(getattr(vm, "stt_provider", "default")),
            "tts_provider": str(getattr(vm, "tts_provider", "default")),
            "initialized": bool(getattr(vm, "_initialized", False)),
        }
