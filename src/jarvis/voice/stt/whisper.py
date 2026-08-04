"""Whisper STT provider — local speech-to-text with faster-whisper.

The model is downloaded on first use and cached locally (see
``voice.stt.model`` and ``voice.stt.download_root`` in jarvis.yaml).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.core.exceptions import VoiceProviderError
from jarvis.voice.audio.wav import pcm_to_wav
from jarvis.voice.base import BaseSTT

logger = logging.getLogger(__name__)


class WhisperProvider(BaseSTT):
    """Local Whisper transcription via ``faster_whisper``."""

    name = "whisper"

    def __init__(self, config: object) -> None:
        super().__init__(config)
        self.model_name = getattr(config, "model", "") or "base"
        self.language = getattr(config, "language", "") or ""
        self.device = getattr(config, "device", "") or "auto"
        self.compute_type = getattr(config, "compute_type", "") or "default"
        self.download_root = getattr(config, "download_root", "") or None
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise VoiceProviderError(
                    "'faster-whisper' is not installed. Run: pip install -e \".[voice]\""
                ) from exc
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.download_root,
            )
            logger.info(f"Loaded Whisper model: {self.model_name}")
        return self._model

    @staticmethod
    def _normalize_language(language: str) -> str | None:
        """Map BCP-47 codes (e.g. 'en-US') to whisper's 2-letter codes ('en')."""
        code = (language or "").strip()
        if not code:
            return None
        return code.split("-")[0].lower()

    def _transcribe_audio(self, model: Any, audio_input: Any) -> str:
        segments, _info = model.transcribe(
            audio_input,
            language=self._normalize_language(self.language),
            beam_size=5,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
    ) -> str:
        model = await asyncio.to_thread(self._get_model)
        wav = pcm_to_wav(audio, sample_rate, sample_width)
        try:
            return await asyncio.to_thread(self._transcribe_audio, model, wav)
        except Exception as exc:
            raise VoiceProviderError(f"Whisper transcription failed: {exc}") from exc

    async def transcribe_file(self, path: str) -> str:
        model = await asyncio.to_thread(self._get_model)
        try:
            return await asyncio.to_thread(self._transcribe_audio, model, path)
        except Exception as exc:
            raise VoiceProviderError(f"Whisper transcription failed: {exc}") from exc
