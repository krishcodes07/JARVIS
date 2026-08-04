"""
Voice subsystem — Text-to-Speech (TTS) and Speech-to-Text (STT).

Providers are configured in ``config/jarvis.yaml``:

- TTS: ``edge_tts`` (free, no key) or ``elevenlabs`` (API key required).
- STT: ``sr`` (speech_recognition) or ``whisper`` (local faster-whisper).

The ``VoiceManager`` is the high-level entry point used by the UIs.
"""

from jarvis.voice.base import BaseSTT, BaseTTS, VoiceInfo
from jarvis.voice.manager import VoiceManager
from jarvis.voice.registry import VoiceRegistry

__all__ = [
    "BaseSTT",
    "BaseTTS",
    "VoiceInfo",
    "VoiceManager",
    "VoiceRegistry",
]
