"""Audio Recorder — voice-activity-detected microphone capture.

Records from the default (or configured) microphone using ``sounddevice`` and
returns raw int16 mono PCM. Speech capture starts once the input energy crosses
the threshold and stops after ``pause_threshold`` seconds of relative silence.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - dependency guard
    sd = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import select
    import sys
except ImportError:
    select = None


def check_keyboard_cancel() -> bool:
    """Check if Ctrl+T (ASCII 20 / 0x14) was pressed in terminal without blocking."""
    if msvcrt is not None:
        try:
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b"\x14":  # Ctrl+T
                    return True
        except Exception:
            pass
    elif select is not None and sys.stdin.isatty():
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == "\x14":  # Ctrl+T
                    return True
        except Exception:
            pass
    return False


class AudioRecorder:
    """Captures a single utterance from the microphone."""

    def __init__(
        self,
        sample_rate: int = 16000,
        device: str | int | None = None,
        energy_threshold: float = 300.0,
        pause_threshold: float = 0.8,
        max_duration: float = 30.0,
        blocksize: int = 1024,
    ) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "Microphone capture requires 'sounddevice' and 'numpy'. "
                f"Install them with: pip install -e \".[voice]\" ({_IMPORT_ERROR})"
            ) from _IMPORT_ERROR
        self.sample_rate = sample_rate
        self.device = device
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.max_duration = max_duration
        self.blocksize = blocksize

    @staticmethod
    def _rms16(block: np.ndarray) -> float:
        """Root-mean-square energy scaled to the int16 range (0-32767)."""
        return float(np.sqrt(np.mean(block**2))) * 32767.0

    async def capture(
        self,
        cancel_checker: Any | None = None,
    ) -> bytes | None:
        """Record one utterance and return raw int16 mono PCM.

        Returns:
            The captured PCM bytes, ``b"__CANCEL_VOICE_MODE__"`` if cancelled (e.g. Ctrl+T),
            or ``None`` if no speech was detected within ``max_duration``.
        """
        if sd is None:
            logger.warning("sounddevice module is not available for audio recording.")
            return None

        audio_queue: Any = collections.deque()

        def callback(indata: np.ndarray, frames: int, time: Any, status: Any) -> None:
            audio_queue.append(indata.copy())

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            blocksize=self.blocksize,
            callback=callback,
        )

        preroll: collections.deque = collections.deque(maxlen=15)
        collected: list[np.ndarray] = []
        speaking = False
        last_speech = 0.0
        started = time.monotonic()

        with stream:
            while time.monotonic() - started <= self.max_duration:
                if (cancel_checker and cancel_checker()) or (cancel_checker is None and check_keyboard_cancel()):
                    return b"__CANCEL_VOICE_MODE__"


                try:
                    block = audio_queue.popleft()
                except IndexError:
                    await asyncio.sleep(0.02)
                    if speaking and time.monotonic() - last_speech > self.pause_threshold:
                        break
                    continue

                preroll.append(block)
                if speaking:
                    collected.append(block)
                    if self._rms16(block) > self.energy_threshold:
                        last_speech = time.monotonic()
                    elif time.monotonic() - last_speech > self.pause_threshold:
                        break
                elif self._rms16(block) > self.energy_threshold:
                    speaking = True
                    last_speech = time.monotonic()
                    collected.extend(list(preroll))

        if not collected:
            return None

        data = np.concatenate(collected)
        return (data * 32767.0).astype(np.int16).tobytes()
