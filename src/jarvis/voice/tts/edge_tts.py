"""Edge TTS provider — Microsoft Edge's neural text-to-speech (free, no API key).

Supports streaming — MP3 chunks are yielded as they arrive from
the Edge TTS service via ``Communicate.stream()``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from jarvis.core.exceptions import VoiceProviderError
from jarvis.voice.base import BaseTTS, VoiceInfo

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-JennyNeural"


class EdgeTTSProvider(BaseTTS):
    """Text-to-speech via Microsoft's online Edge TTS service.

    Streaming is supported — MP3 chunks are yielded as they arrive.
    Requires network access but no API key.
    """

    name = "edge_tts"

    def __init__(self, config: object) -> None:
        super().__init__(config)
        self.default_voice = getattr(config, "voice", "") or DEFAULT_VOICE

    def _resolve_voice(self, voice: str | None) -> str:
        return voice or self.default_voice or DEFAULT_VOICE

    @property
    def supports_streaming(self) -> bool:
        return True

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize by collecting all streamed chunks."""
        chunks = [chunk async for chunk in self.stream(text, voice)]
        return b"".join(chunks)

    async def stream(self, text: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """Stream MP3 audio chunks as they arrive from Edge TTS."""
        try:
            import edge_tts
        except ImportError as exc:
            raise VoiceProviderError(
                "The 'edge-tts' package is not installed. Run: pip install -e \".[voice]\""
            ) from exc

        target_voice = self._resolve_voice(voice)
        rate = getattr(self.config, "rate", "") or "+0%"
        volume = getattr(self.config, "volume", "") or "+0%"
        pitch = getattr(self.config, "pitch", "") or "+0Hz"

        try:
            communicate = edge_tts.Communicate(
                text,
                target_voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk["data"]:
                    yield chunk["data"]
        except Exception as exc:
            if target_voice != DEFAULT_VOICE:
                logger.warning(
                    f"EdgeTTS stream failed for voice '{target_voice}' ({exc}); "
                    f"falling back to '{DEFAULT_VOICE}'."
                )
                communicate = edge_tts.Communicate(
                    text,
                    DEFAULT_VOICE,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio" and chunk["data"]:
                        yield chunk["data"]
            else:
                raise VoiceProviderError(f"EdgeTTS synthesis failed: {exc}") from exc

    async def list_voices(self) -> list[VoiceInfo]:
        try:
            import edge_tts
        except ImportError as exc:
            raise VoiceProviderError(
                "The 'edge-tts' package is not installed. Run: pip install -e \".[voice]\""
            ) from exc

        voices = await edge_tts.list_voices()
        result: list[VoiceInfo] = []
        for v in voices:
            if not isinstance(v, dict):
                v = v.__dict__
            result.append(
                VoiceInfo(
                    id=v.get("ShortName", "") or v.get("Name", ""),
                    name=v.get("FriendlyName", ""),
                    gender=v.get("Gender", None),
                    locale=v.get("Locale", None),
                )
            )
        return result
