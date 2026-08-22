"""Voice Manager — coordinates TTS, STT and audio I/O for the voice subsystem.

This is the high-level interface used by the UIs:

- **text mode:** input/output through the keyboard and screen only.
- **voice mode:** JARVIS listens (STT) and speaks (TTS).

Modes can be toggled at runtime (``toggle_mode``) and the default is set in
``config/jarvis.yaml`` (``voice.mode``).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from jarvis.core.exceptions import VoiceError
from jarvis.voice.audio.player import AudioPlayer
from jarvis.voice.audio.recorder import AudioRecorder
from jarvis.voice.base import BaseSTT, BaseTTS
from jarvis.voice.registry import VoiceRegistry
from jarvis.voice.utils import strip_markdown_for_speech

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig

logger = logging.getLogger(__name__)


class VoiceManager:
    """High-level voice interface used by the UIs.

    Usage:
        ```python
        manager = VoiceManager(config)
        await manager.initialize()
        text = await manager.listen()      # mic -> text
        await manager.speak(text)          # text -> speaker (auto-selects streaming)
        manager.stop()                     # immediately stop audio
        await manager.shutdown()
        ```
    """

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config.voice
        self.tts: BaseTTS | None = None
        self.stt: BaseSTT | None = None
        self.recorder: AudioRecorder | None = None
        self.player: AudioPlayer | None = None
        self._initialized = False
        self._background_tasks: set[asyncio.Task] = set()

    async def initialize(self) -> None:
        """Create the configured TTS/STT providers and audio I/O devices."""
        if not self.config.enabled:
            logger.info("Voice is disabled in config.")
            return

        registry = VoiceRegistry()
        self.tts = registry.create_tts(self.config.tts)
        self.stt = registry.create_stt(self.config.stt)
        self.recorder = AudioRecorder(
            sample_rate=self.config.stt.sample_rate or 16000,
            device=self.config.audio.input_device,
            energy_threshold=self.config.stt.energy_threshold,
            pause_threshold=self.config.stt.pause_threshold,
            max_duration=self.config.stt.max_duration,
        )
        self.player = AudioPlayer(
            sample_rate=self.config.audio.sample_rate or 44100,
            device=self.config.audio.output_device,
        )
        self._initialized = True
        logger.info(
            f"Voice initialized (TTS={self.config.tts.provider}, "
            f"STT={self.config.stt.provider}, mode={self.config.mode})."
        )

    # ─── Mode ────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """Current voice mode: 'text' or 'voice'."""
        return self.config.mode

    def set_mode(self, mode: str) -> None:
        """Set the voice mode ('text' or 'voice')."""
        if mode not in ("text", "voice"):
            raise VoiceError(f"Unknown voice mode: {mode}")
        self.config.mode = mode
        logger.info(f"Voice mode set to '{mode}'.")

    def toggle_mode(self) -> str:
        """Toggle between text and voice mode; returns the new mode."""
        self.set_mode("text" if self.mode == "voice" else "voice")
        return self.mode

    # ─── Stop ────────────────────────────────────────────────

    def stop(self) -> None:
        """Immediately stop any audio playback or recording."""
        if self.player is not None:
            self.player.stop()
        logger.debug("Voice playback stopped.")

    # ─── Speaking ────────────────────────────────────────────

    def _truncate_for_speech(self, text: str) -> str:
        """Apply max_speak_characters limit if configured (0 or None means unlimited)."""
        max_chars = getattr(self.config, "max_speak_characters", 0)
        if max_chars is None:
            max_chars = getattr(self.config, "max_characters", 0)
        if max_chars is not None and int(max_chars) > 0 and len(text) > int(max_chars):
            logger.info(
                f"Voice output truncated from {len(text)} to {max_chars} characters "
                "(configured by voice.max_speak_characters)."
            )
            return text[: int(max_chars)].rstrip()
        return text

    async def speak(self, text: str, voice: str | None = None) -> None:
        """Synthesize and play text through the speaker.

        Automatically strips markdown syntax formatting (*, #, `, [], etc.),
        applies max_speak_characters length constraints, and uses streaming
        when the TTS provider supports it.
        """
        if not self._initialized or self.tts is None or self.player is None:
            return
        if not text or not text.strip():
            return

        clean_text = strip_markdown_for_speech(text)
        clean_text = self._truncate_for_speech(clean_text)
        if not clean_text:
            return

        if self.tts.supports_streaming:
            await self.speak_stream(clean_text, voice)
        else:
            audio = await self.tts.synthesize(clean_text, voice)
            await self.player.play_bytes(audio)

    async def speak_stream(self, text: str, voice: str | None = None) -> None:
        """Synthesize and play text with streaming TTS when supported."""
        if not self._initialized or self.tts is None or self.player is None:
            return
        clean_text = strip_markdown_for_speech(text)
        clean_text = self._truncate_for_speech(clean_text)
        if not clean_text:
            return
        await self.player.play_stream(self.tts.stream(clean_text, voice))

    def speak_in_background(self, text: str) -> None:
        """Play text without blocking the caller (fire-and-forget task)."""
        task = asyncio.create_task(self.speak(text))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    # ─── Listening ───────────────────────────────────────────

    async def listen(self, cancel_checker: Any | None = None) -> str:
        """Capture one utterance from the mic and transcribe it.

        Returns:
            The transcribed text, ``"__CANCEL_VOICE_MODE__"`` if cancelled (e.g. Ctrl+T),
            or ``""`` if nothing was heard.
        """
        if not self._initialized or self.stt is None or self.recorder is None:
            return ""
        pcm = await self.recorder.capture(cancel_checker=cancel_checker)
        if pcm == b"__CANCEL_VOICE_MODE__":
            return "__CANCEL_VOICE_MODE__"
        if not pcm:
            return ""
        return await self.stt.transcribe(pcm, self.recorder.sample_rate, 2)

    async def transcribe_file(self, path: str) -> str:
        """Transcribe an audio file using the configured STT provider."""
        if not self._initialized or self.stt is None:
            return ""
        return await self.stt.transcribe_file(path)

    # ─── Providers & voices ──────────────────────────────────

    async def list_voices(self) -> list[Any]:
        """List voices available from the active TTS provider."""
        if self.tts is None:
            return []
        return await self.tts.list_voices()

    async def switch_tts_provider(self, name: str) -> None:
        """Hot-switch the TTS provider (updates config + rebuilds instance)."""
        self.config.tts.provider = name
        registry = VoiceRegistry()
        if self.tts is not None:
            await self.tts.close()
        self.tts = registry.create_tts(self.config.tts)
        logger.info(f"TTS provider switched to '{name}'.")

    async def switch_stt_provider(self, name: str) -> None:
        """Hot-switch the STT provider (updates config + rebuilds instance)."""
        self.config.stt.provider = name
        registry = VoiceRegistry()
        if self.stt is not None:
            await self.stt.close()
        self.stt = registry.create_stt(self.config.stt)
        logger.info(f"STT provider switched to '{name}'.")

    # ─── Lifecycle ───────────────────────────────────────────

    async def shutdown(self) -> None:
        """Release all voice providers and audio devices."""
        if self.tts is not None:
            await self.tts.close()
        if self.stt is not None:
            await self.stt.close()
        if self.player is not None:
            await self.player.close()
        self._initialized = False
        logger.info("Voice manager shut down.")
