"""
Voice — Abstract base interfaces for TTS and STT providers.

Voice providers follow the same pattern as LLM providers: each provider is a
small class implementing a common interface, and the active provider is chosen
from ``config/jarvis.yaml`` (``voice.tts.provider`` / ``voice.stt.provider``).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VoiceInfo:
    """A single TTS voice exposed by a provider."""

    id: str
    name: str = ""
    gender: str | None = None
    locale: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTTS(ABC):
    """Abstract interface for text-to-speech providers.

    Subclasses must implement ``synthesize`` and ``list_voices``.
    ``stream`` is optional — providers that cannot stream incrementally
    should override ``supports_streaming`` to ``False``.
    """

    name: str = "base"

    def __init__(self, config: Any) -> None:
        self.config = config

    @property
    def supports_streaming(self) -> bool:
        """Whether the provider can stream audio incrementally."""
        return True

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize speech and return the complete audio blob (e.g. MP3)."""

    def stream(self, text: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """Stream audio chunks as they are generated.

        Yields:
            Audio bytes (MP3 by default) as they become available.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support streaming TTS."
        )

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]:
        """List voices available from the provider."""

    async def close(self) -> None:
        """Release any provider resources."""
        logger.debug(f"{type(self).__name__}.close() called (no-op)")


class BaseSTT(ABC):
    """Abstract interface for speech-to-text providers."""

    name: str = "base"

    def __init__(self, config: Any) -> None:
        self.config = config

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
    ) -> str:
        """Transcribe raw PCM audio (mono, little-endian, signed) to text."""

    @abstractmethod
    async def transcribe_file(self, path: str) -> str:
        """Transcribe an audio file on disk to text."""

    async def close(self) -> None:
        """Release any provider resources."""
        logger.debug(f"{type(self).__name__}.close() called (no-op)")
