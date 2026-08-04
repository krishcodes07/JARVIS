"""Voice Registry — maps configured provider names to provider classes."""

from __future__ import annotations

import logging

from jarvis.core.exceptions import VoiceConfigError
from jarvis.voice.base import BaseSTT, BaseTTS

logger = logging.getLogger(__name__)

TTS_PROVIDERS = ("edge_tts", "elevenlabs")
STT_PROVIDERS = ("sr", "whisper")


class VoiceRegistry:
    """Creates TTS/STT provider instances from configuration."""

    def create_tts(self, config: object) -> BaseTTS:
        """Instantiate the configured TTS provider."""
        provider = (getattr(config, "provider", "") or "").lower()
        if provider == "edge_tts":
            from jarvis.voice.tts.edge_tts import EdgeTTSProvider

            return EdgeTTSProvider(config)
        if provider == "elevenlabs":
            from jarvis.voice.tts.elevenlabs import ElevenLabsProvider

            return ElevenLabsProvider(config)
        raise VoiceConfigError(
            f"Unknown TTS provider: '{provider}'. Available: {', '.join(TTS_PROVIDERS)}"
        )

    def create_stt(self, config: object) -> BaseSTT:
        """Instantiate the configured STT provider."""
        provider = (getattr(config, "provider", "") or "").lower()
        if provider == "sr":
            from jarvis.voice.stt.speech_recognition import SpeechRecognitionProvider

            return SpeechRecognitionProvider(config)
        if provider == "whisper":
            from jarvis.voice.stt.whisper import WhisperProvider

            return WhisperProvider(config)
        raise VoiceConfigError(
            f"Unknown STT provider: '{provider}'. Available: {', '.join(STT_PROVIDERS)}"
        )
