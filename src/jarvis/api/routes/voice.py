"""
JARVIS Voice API — Endpoints for speech synthesis (TTS), speech-to-text (STT), and voice status.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from jarvis.api.deps import get_engine
from jarvis.core.exceptions import VoiceError
from jarvis.voice.registry import TTS_PROVIDERS, VoiceRegistry, list_voices_for_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to speak")
    voice: str | None = Field(default=None, description="Optional voice ID override")
    provider: str | None = Field(
        default=None, description="Optional TTS provider override (for settings previews)"
    )


class ModeRequest(BaseModel):
    mode: str = Field(..., description="Target mode ('text' or 'voice')")


@router.get("/status")
async def get_voice_status() -> dict[str, Any]:
    """Get current voice subsystem configuration and active provider status."""
    engine = get_engine()
    if not engine or not engine.voice_manager:
        return {
            "enabled": False,
            "mode": "text",
            "tts_provider": "edge_tts",
            "stt_provider": "whisper",
            "active_voice": "",
        }

    vm = engine.voice_manager
    cfg = vm.config
    return {
        "enabled": cfg.enabled,
        "mode": vm.mode,
        "tts_provider": cfg.tts.provider,
        "stt_provider": cfg.stt.provider,
        "active_voice": cfg.tts.voice or "",
    }


@router.get("/providers")
async def list_tts_providers() -> list[dict[str, Any]]:
    """List the TTS providers this build can construct, flagging the active one."""
    engine = get_engine()
    active = "edge_tts"
    if engine and engine.config:
        active = engine.config.voice.tts.provider or active

    return [{"id": name, "active": name == active} for name in TTS_PROVIDERS]


@router.get("/voices")
async def list_voices(provider: str | None = None) -> list[dict[str, Any]]:
    """List available TTS voices, optionally for a provider other than the active one.

    The settings panel calls this with ``?provider=elevenlabs`` the moment the
    dropdown changes — before the choice is saved — so it must not depend on a
    live ``VoiceManager`` (which only exists while voice is enabled).
    """
    engine = get_engine()
    tts_cfg = engine.config.voice.tts if (engine and engine.config) else None
    target = (provider or (tts_cfg.provider if tts_cfg else "") or "edge_tts").strip().lower()

    try:
        voices = await list_voices_for_provider(target, tts_cfg)
    except VoiceError as e:
        # Missing API key, provider package, or unknown provider — the message is
        # actionable, so surface it instead of an empty list.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.debug(f"Could not list {target} voices: {e}")
        raise HTTPException(status_code=502, detail=f"Could not reach {target}: {e}")

    return [
        {
            "id": getattr(v, "id", str(v)),
            "name": getattr(v, "name", "") or getattr(v, "id", str(v)),
            "gender": getattr(v, "gender", None) or "",
            "locale": getattr(v, "locale", None) or "",
        }
        for v in voices
    ]


@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest) -> Response:
    """Convert text into speech audio bytes (MP3 / WAV).

    Falls back to a throwaway provider instance when the live voice manager is
    unavailable (voice disabled) or when a different provider was requested, so
    the settings preview works before the change is saved.
    """
    engine = get_engine()
    tts_cfg = engine.config.voice.tts if (engine and engine.config) else None
    active_provider = (tts_cfg.provider if tts_cfg else "") or "edge_tts"
    target = (request.provider or active_provider).strip().lower()

    live_tts = getattr(engine.voice_manager, "tts", None) if engine and engine.voice_manager else None

    try:
        if live_tts is not None and target == active_provider.strip().lower():
            audio_bytes = await live_tts.synthesize(request.text, voice=request.voice)
        else:
            audio_bytes = await _synthesize_adhoc(target, tts_cfg, request.text, request.voice)
    except VoiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Synthesis error")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {e}")

    if not audio_bytes:
        raise HTTPException(status_code=502, detail=f"{target} returned no audio.")

    return Response(content=audio_bytes, media_type="audio/mpeg")


async def _synthesize_adhoc(
    provider: str,
    tts_cfg: Any | None,
    text: str,
    voice: str | None,
) -> bytes:
    """Synthesize through a short-lived provider instance, then release it."""
    if tts_cfg is not None and hasattr(tts_cfg, "model_copy"):
        cfg: Any = tts_cfg.model_copy(update={"provider": provider})
    else:
        from jarvis.core.config import TTSConfig

        cfg = TTSConfig(provider=provider)

    tts = VoiceRegistry().create_tts(cfg)
    try:
        return await tts.synthesize(text, voice=voice)
    finally:
        with contextlib.suppress(Exception):
            await tts.close()


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe an uploaded audio blob from the browser microphone.

    Falls back to an ad-hoc STT provider built from ``config.voice.stt`` when the
    live voice manager is unavailable, so browser dictation works even with voice
    output disabled.
    """
    engine = get_engine()
    suffix = (
        f".{file.filename.split('.')[-1]}" if file.filename and "." in file.filename else ".wav"
    )

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
    except Exception as e:
        logger.exception("Could not buffer uploaded audio")
        raise HTTPException(status_code=500, detail=f"Could not read uploaded audio: {e}")

    try:
        vm = engine.voice_manager if engine else None
        if vm is not None:
            text = await vm.transcribe_file(tmp_path)
        else:
            stt_cfg = engine.config.voice.stt if (engine and engine.config) else None
            text = await _transcribe_adhoc(stt_cfg, tmp_path)
    except VoiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Transcription error")
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {e}")
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)

    return {"text": text or ""}


async def _transcribe_adhoc(stt_cfg: Any | None, path: str) -> str:
    """Transcribe through a short-lived STT provider instance, then release it."""
    if stt_cfg is None:
        from jarvis.core.config import STTConfig

        cfg: Any = STTConfig()
    else:
        cfg = stt_cfg

    stt = VoiceRegistry().create_stt(cfg)
    try:
        return await stt.transcribe_file(path)
    finally:
        with contextlib.suppress(Exception):
            await stt.close()


@router.post("/mode")
async def set_voice_mode(request: ModeRequest) -> dict[str, str]:
    """Switch voice mode ('text' or 'voice').

    Persists to config even when no voice manager is live, so the toggle sticks
    and takes effect the next time voice is enabled.
    """
    mode = (request.mode or "").strip().lower()
    if mode not in ("text", "voice"):
        raise HTTPException(status_code=400, detail="Mode must be 'text' or 'voice'.")

    engine = get_engine()
    if engine and engine.voice_manager:
        engine.voice_manager.set_mode(mode)

    if engine and engine.config:
        engine.config.voice.mode = mode
        with contextlib.suppress(Exception):
            engine.config.save()

    return {"status": "success", "mode": mode}
