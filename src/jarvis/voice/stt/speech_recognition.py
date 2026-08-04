"""SpeechRecognition STT provider — uses the SpeechRecognition library.

Supports multiple recognition engines: Google's free web API (default),
local Whisper (via openai-whisper), Sphinx, Vosk, etc. Live capture uses the
shared sounddevice recorder — pyaudio is NOT required.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.core.exceptions import VoiceProviderError
from jarvis.voice.base import BaseSTT

logger = logging.getLogger(__name__)


class SpeechRecognitionProvider(BaseSTT):
    """Speech-to-text via ``speech_recognition``."""

    name = "sr"

    def __init__(self, config: object) -> None:
        super().__init__(config)
        self.engine = getattr(config, "engine", "") or "google"
        self.language = getattr(config, "language", "") or "en-US"

    def _build_recognizer(self) -> Any:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = getattr(self.config, "energy_threshold", 300.0)
        recognizer.pause_threshold = getattr(self.config, "pause_threshold", 0.8)
        return recognizer

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
    ) -> str:
        import speech_recognition as sr

        recognizer = self._build_recognizer()
        audio_data = sr.AudioData(audio, sample_rate, sample_width)
        return await self._recognize(recognizer, audio_data)

    async def transcribe_file(self, path: str) -> str:
        import speech_recognition as sr

        recognizer = self._build_recognizer()
        with sr.AudioFile(path) as source:
            audio_data = recognizer.record(source)
        return await self._recognize(recognizer, audio_data)

    async def _recognize(self, recognizer: Any, audio_data: Any) -> str:
        import speech_recognition as sr

        engine = self.engine.lower()

        def recognize() -> str:
            if engine == "google":
                return recognizer.recognize_google(audio_data, language=self.language)
            if engine == "whisper":
                return recognizer.recognize_whisper(audio_data, language=self.language)
            if engine == "sphinx":
                return recognizer.recognize_sphinx(audio_data, language=self.language)
            if engine == "vosk":
                return recognizer.recognize_vosk(audio_data)
            raise VoiceProviderError(
                f"Unknown speech_recognition engine: '{engine}'. "
                "Supported: google, whisper, sphinx, vosk."
            )

        loop = asyncio.get_running_loop()
        try:
            text = await loop.run_in_executor(None, recognize)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            raise VoiceProviderError(
                f"STT engine '{engine}' request failed: {exc}"
            ) from exc
        except Exception as exc:
            raise VoiceProviderError(f"STT engine '{engine}' failed: {exc}") from exc
        return (text or "").strip()
