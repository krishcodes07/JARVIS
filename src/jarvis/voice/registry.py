"""Voice Registry — maps configured provider names to provider classes."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from jarvis.core.exceptions import VoiceConfigError
from jarvis.voice.base import BaseSTT, BaseTTS, VoiceInfo

logger = logging.getLogger(__name__)

TTS_PROVIDERS = ("edge_tts", "elevenlabs")
STT_PROVIDERS = ("sr", "whisper")

# Voice catalogues are stable and expensive to fetch (edge_tts pulls ~500 entries
# over the network, ElevenLabs costs an API round-trip), so they are memoised per
# provider for the life of the process.
_VOICE_CACHE: dict[str, list[VoiceInfo]] = {}


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


async def list_voices_for_provider(
    provider: str,
    tts_config: Any | None = None,
    use_cache: bool = True,
) -> list[VoiceInfo]:
    """List the voices a TTS provider offers, without touching the live manager.

    The settings UI needs to preview another provider's catalogue *before* the
    switch is saved, and the active :class:`~jarvis.voice.manager.VoiceManager`
    only exists when voice is enabled. This builds a throwaway provider instance
    instead.

    Args:
        provider: Target provider name (``edge_tts`` or ``elevenlabs``).
        tts_config: Optional ``TTSConfig`` to inherit credentials/model from. Its
            ``provider`` field is overridden with ``provider``.
        use_cache: Reuse a previously fetched catalogue for this provider.

    Returns:
        The provider's voices, or an empty list if it reports none.

    Raises:
        VoiceConfigError: Unknown provider name.
        VoiceAuthError / VoiceProviderError: Provider could not be constructed
            (missing API key, package not installed).
    """
    key = (provider or "").strip().lower()
    if not key:
        raise VoiceConfigError("No TTS provider specified.")

    if use_cache and key in _VOICE_CACHE:
        return _VOICE_CACHE[key]

    if tts_config is None:
        from jarvis.core.config import TTSConfig

        cfg: Any = TTSConfig(provider=key)
    elif hasattr(tts_config, "model_copy"):
        cfg = tts_config.model_copy(update={"provider": key})
    else:
        cfg = tts_config

    tts = VoiceRegistry().create_tts(cfg)
    try:
        voices = await tts.list_voices()
    finally:
        with contextlib.suppress(Exception):
            await tts.close()

    if voices:
        _VOICE_CACHE[key] = voices
    return voices


def clear_voice_cache(provider: str | None = None) -> None:
    """Drop the memoised voice catalogue for one provider, or all of them."""
    if provider is None:
        _VOICE_CACHE.clear()
    else:
        _VOICE_CACHE.pop(provider.strip().lower(), None)
