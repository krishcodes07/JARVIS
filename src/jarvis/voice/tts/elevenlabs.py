"""ElevenLabs TTS provider — high-quality neural voices (requires API key).

Supports true streaming audio synthesis via ``text_to_speech.stream`` which
yields chunks with much lower latency. Requires ``ELEVENLABS_API_KEY`` in ``.env``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from jarvis.core.exceptions import VoiceAuthError, VoiceProviderError
from jarvis.voice.base import BaseTTS, VoiceInfo

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsProvider(BaseTTS):
    """Text-to-speech via the ElevenLabs API (streaming supported).

    Uses the ``text_to_speech.stream`` endpoint for low-latency streaming and
    ``text_to_speech.convert`` for single-shot synthesis.
    """

    name = "elevenlabs"

    def __init__(self, config: object) -> None:
        super().__init__(config)
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            raise VoiceAuthError(
                "ELEVENLABS_API_KEY is not set. Add it to your .env file "
                "or switch the TTS provider to 'edge_tts' in config/jarvis.yaml."
            )
        try:
            from elevenlabs import AsyncElevenLabs
        except ImportError as exc:
            raise VoiceProviderError(
                "The 'elevenlabs' package is not installed. Run: pip install -e \".[voice]\""
            ) from exc

        self._client = AsyncElevenLabs(api_key=api_key)
        self.default_voice = getattr(config, "voice", "") or ""
        self.model = getattr(config, "model", "") or DEFAULT_MODEL
        self.output_format = getattr(config, "output_format", "") or DEFAULT_OUTPUT_FORMAT
        self.optimize_streaming_latency = getattr(config, "optimize_streaming_latency", None)
        self._cached_voices: list[VoiceInfo] | None = None

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _resolve_voice(self, voice: str | None) -> str:
        target = (voice or self.default_voice or "").strip()
        # If no voice is specified or default is the edge_tts placeholder
        if not target or target.startswith("en-US-"):
            voices = await self.list_voices()
            if not voices:
                return "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs Rachel ID fallback
            logger.info(f"Using ElevenLabs voice '{voices[0].name}' ({voices[0].id})")
            return voices[0].id

        voices = await self.list_voices()
        target_lower = target.lower()
        for v in voices:
            if v.id == target or v.name.lower() == target_lower:
                return v.id

        # If not matching listed names/IDs, check if it's a direct voice ID string
        if not any(target_lower.startswith(prefix) for prefix in ("en-", "es-", "fr-", "de-", "zh-", "ja-")):
            return target

        if voices:
            logger.warning(
                f"Voice '{target}' not found in ElevenLabs account. Falling back to '{voices[0].name}' ({voices[0].id})."
            )
            return voices[0].id

        return "21m00Tcm4TlvDq8ikWAM"

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        voice_id = await self._resolve_voice(voice)
        try:
            chunks = []
            async for chunk in self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self.model,
                output_format=self.output_format,
            ):
                if chunk:
                    chunks.append(chunk)
            return b"".join(chunks)
        except Exception:
            # Fallback to collecting stream chunks if convert raises
            chunks = [chunk async for chunk in self.stream(text, voice)]
            return b"".join(chunks)

    async def stream(self, text: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks using the ElevenLabs streaming endpoint (text_to_speech.stream)."""
        voice_id = await self._resolve_voice(voice)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                stream_kwargs: dict[str, Any] = {
                    "voice_id": voice_id,
                    "text": text,
                    "model_id": self.model,
                    "output_format": self.output_format,
                }
                if self.optimize_streaming_latency is not None:
                    stream_kwargs["optimize_streaming_latency"] = self.optimize_streaming_latency

                audio_stream = self._client.text_to_speech.stream(**stream_kwargs)
                async for chunk in audio_stream:
                    if chunk:
                        yield chunk
                return
            except Exception as e:
                err_msg = str(e)
                if (
                    "429" in err_msg
                    or "concurrent_limit" in err_msg
                    or "rate_limit" in err_msg
                ) and attempt < max_retries - 1:
                    logger.warning(
                        f"ElevenLabs rate limit hit. Retrying in 1.0s (attempt {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(1.0)
                    continue
                raise VoiceProviderError(f"ElevenLabs streaming synthesis failed: {e}") from e

    async def list_voices(self) -> list[VoiceInfo]:
        if self._cached_voices is not None:
            return self._cached_voices
        try:
            response = await self._client.voices.get_all()
            self._cached_voices = [
                VoiceInfo(id=voice.voice_id, name=getattr(voice, "name", "") or voice.voice_id)
                for voice in response.voices
            ]
            return self._cached_voices
        except Exception as e:
            logger.warning(f"Failed to list ElevenLabs voices: {e}")
            return []
