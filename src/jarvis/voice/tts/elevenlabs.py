"""ElevenLabs TTS provider — high-quality neural voices (requires API key).

Supports true streaming audio synthesis via ``text_to_speech.stream`` which
yields chunks with much lower latency. Requires ``ELEVENLABS_API_KEY`` in ``.env``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from jarvis.core.exceptions import VoiceAuthError, VoiceProviderError
from jarvis.voice.base import BaseTTS, VoiceInfo

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsProvider(BaseTTS):
    """Text-to-speech via the ElevenLabs API (streaming supported).

    Uses the ``text_to_speech.convert`` endpoint for non-streaming and
    ``text_to_speech.stream`` for true streaming with lower latency.
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

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _resolve_voice(self, voice: str | None) -> str:
        voice_id = voice or self.default_voice
        if voice_id:
            return voice_id
        voices = await self.list_voices()
        if not voices:
            raise VoiceProviderError("No ElevenLabs voices available for this account.")
        logger.info(f"Using first available ElevenLabs voice: {voices[0].id}")
        return voices[0].id

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        chunks = [chunk async for chunk in self.stream(text, voice)]
        return b"".join(chunks)

    async def stream(self, text: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks using the ElevenLabs streaming endpoint.

        Uses ``text_to_speech.convert`` which already returns an async iterator
        of audio bytes. The ElevenLabs SDK handles the streaming internally.
        """
        voice_id = await self._resolve_voice(voice)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async for chunk in self._client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id=self.model,
                    output_format=self.output_format,
                ):
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
                raise VoiceProviderError(f"ElevenLabs synthesis failed: {e}") from e

    async def list_voices(self) -> list[VoiceInfo]:
        try:
            response = await self._client.voices.get_all()
        except Exception as e:
            raise VoiceProviderError(f"Failed to list ElevenLabs voices: {e}") from e
        return [
            VoiceInfo(id=voice.voice_id, name=getattr(voice, "name", "") or voice.voice_id)
            for voice in response.voices
        ]
