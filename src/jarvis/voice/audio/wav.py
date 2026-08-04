"""Audio helpers — PCM <-> WAV conversion (stdlib only)."""

from __future__ import annotations

import io
import wave


def pcm_to_wav(
    audio: bytes,
    sample_rate: int,
    sample_width: int = 2,
    channels: int = 1,
) -> io.BytesIO:
    """Wrap raw PCM audio in a WAV container.

    Most STT engines (speech_recognition, faster-whisper) expect WAV input,
    while the microphone recorder produces raw PCM bytes.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(audio)
    buffer.seek(0)
    return buffer
