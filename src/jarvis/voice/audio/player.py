"""Audio Player — decodes and plays synthesized speech.

Uses ``miniaudio`` to decode MP3/WAV bytes into raw float32/int16 samples and
``sounddevice`` or ``pyaudio`` to play them through the output device.

For streaming TTS, buffers incoming MP3 audio chunks into smooth 12KB blocks
before decoding and writing to PyAudio. This eliminates MP3 frame boundary
artifacts, clicks, pops, and buffer underruns while starting playback
almost instantly (~100ms latency).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import AsyncIterator

import numpy as np

logger = logging.getLogger(__name__)

try:
    import miniaudio
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - dependency guard
    miniaudio = None
    sd = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    import pyaudio as _pyaudio
except ImportError:
    _pyaudio = None


class AudioPlayer:
    """Plays synthesized audio (single-shot or streaming).

    Provides a ``stop()`` method to immediately halt any active playback,
    used by the Esc key handler in the TUI.
    """

    def __init__(self, sample_rate: int = 44100, device: str | int | None = None) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "Audio playback requires 'sounddevice', 'numpy' and 'miniaudio'. "
                f"Install them with: pip install -e \".[voice]\" ({_IMPORT_ERROR})"
            ) from _IMPORT_ERROR
        self.sample_rate = sample_rate
        self.device = device
        self._stop_event = threading.Event()
        self._pa_stream = None  # active pyaudio stream reference for stop()

    def decode(self, data: bytes) -> np.ndarray | None:
        """Decode an MP3/WAV blob to a mono signed 16-bit PCM array at ``self.sample_rate``."""
        if miniaudio is None:
            logger.warning("miniaudio module is not available for audio decoding.")
            return None
        try:
            decoded = miniaudio.decode(
                data,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=self.sample_rate,
            )
        except Exception as e:
            logger.warning(f"Audio decode failed (skipping chunk): {e}")
            return None
        return np.asarray(decoded.samples, dtype=np.int16)

    def decode_float32(self, data: bytes) -> np.ndarray | None:
        """Decode an MP3/WAV blob to a mono float32 array at ``self.sample_rate``."""
        if miniaudio is None:
            return None
        try:
            decoded = miniaudio.decode(
                data,
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=1,
                sample_rate=self.sample_rate,
            )
        except Exception as e:
            logger.warning(f"Audio decode failed (skipping chunk): {e}")
            return None
        return np.asarray(decoded.samples, dtype=np.float32).reshape(-1)

    def stop(self) -> None:
        """Signal any active playback to stop immediately."""
        self._stop_event.set()
        # Stop sounddevice playback
        if sd is not None:
            with contextlib.suppress(Exception):
                sd.stop()


    async def play_bytes(self, data: bytes) -> None:
        """Decode and play a complete audio blob, blocking until finished or stopped."""
        if sd is None:
            logger.warning("sounddevice module is not available for audio playback.")
            return

        self._stop_event.clear()
        samples = await asyncio.to_thread(self.decode_float32, data)
        if samples is None or len(samples) == 0:
            return

        if self._stop_event.is_set():
            return

        await asyncio.to_thread(sd.play, samples, self.sample_rate, device=self.device)

        # Wait for playback to finish, checking stop event periodically
        if not self._stop_event.is_set():
            try:
                await asyncio.to_thread(sd.wait)
            except Exception:
                pass

    async def play_stream(self, chunks: AsyncIterator[bytes]) -> None:
        """Play a stream of audio chunks with smooth, low-latency progressive streaming.

        Buffers incoming audio chunks into smooth MP3 blocks (~12KB) before
        decoding to PCM and writing to PyAudio. This eliminates MP3 frame
        decoding boundary artifacts, clicks, pops, and buffer underruns while
        starting playback almost instantly (~100ms latency).

        Falls back to accumulate-then-play if pyaudio is unavailable.
        """
        if _pyaudio is None or miniaudio is None:
            return await self._play_stream_fallback(chunks)

        self._stop_event.clear()

        pa = _pyaudio.PyAudio()
        stream = pa.open(
            format=_pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True,
        )
        self._pa_stream = stream

        mp3_buffer = bytearray()
        target_buffer_size = 2048  # Initial 2KB buffer (~100ms) for ultra-fast startup

        try:
            async for chunk in chunks:
                if self._stop_event.is_set():
                    return
                if not chunk:
                    continue

                mp3_buffer.extend(chunk)

                if len(mp3_buffer) >= target_buffer_size:
                    data = bytes(mp3_buffer)
                    mp3_buffer.clear()
                    target_buffer_size = 8192  # Ramp to 8KB for smooth continuous playback

                    samples = await asyncio.to_thread(self.decode, data)
                    if samples is None or len(samples) == 0:
                        continue

                    if self._stop_event.is_set():
                        return

                    await asyncio.to_thread(stream.write, samples.tobytes())

            # Decode and play any remaining trailing buffer
            if mp3_buffer and not self._stop_event.is_set():
                data = bytes(mp3_buffer)
                mp3_buffer.clear()

                samples = await asyncio.to_thread(self.decode, data)
                if samples is not None and len(samples) > 0 and not self._stop_event.is_set():
                    await asyncio.to_thread(stream.write, samples.tobytes())

        except Exception as e:
            if not self._stop_event.is_set():
                logger.warning(f"Streaming playback error: {e}")
        finally:
            self._pa_stream = None
            with contextlib.suppress(Exception):
                stream.stop_stream()
                stream.close()
            with contextlib.suppress(Exception):
                pa.terminate()

    async def _play_stream_fallback(self, chunks: AsyncIterator[bytes]) -> None:
        """Fallback: accumulate all chunks then play via sounddevice."""
        self._stop_event.clear()
        raw_buffer = bytearray()

        async for chunk in chunks:
            if self._stop_event.is_set():
                return
            if chunk:
                raw_buffer.extend(chunk)

        if not raw_buffer or self._stop_event.is_set():
            return

        await self.play_bytes(bytes(raw_buffer))

    async def close(self) -> None:
        """Stop any running playback and release the audio device."""
        self.stop()
