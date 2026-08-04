"""
Unit tests for the voice subsystem — no audio hardware or network required.
"""

import io

import pytest


class TestVoiceRegistry:
    """Provider instantiation from config objects."""

    def test_known_tts_providers_registered(self):
        from jarvis.voice.registry import STT_PROVIDERS, TTS_PROVIDERS, VoiceRegistry

        assert TTS_PROVIDERS == ("edge_tts", "elevenlabs")
        assert STT_PROVIDERS == ("sr", "whisper")
        assert VoiceRegistry() is not None

    def test_create_edge_tts_provider(self):
        from jarvis.voice.registry import VoiceRegistry
        from jarvis.voice.tts.edge_tts import EdgeTTSProvider

        class Cfg:
            provider = "edge_tts"

        provider = VoiceRegistry().create_tts(Cfg())
        assert isinstance(provider, EdgeTTSProvider)

    @pytest.mark.asyncio
    async def test_edge_tts_fallback_on_invalid_voice(self):
        from jarvis.voice.tts.edge_tts import DEFAULT_VOICE, EdgeTTSProvider

        class Cfg:
            provider = "edge_tts"
            voice = "invalid-voice-name-xyz"

        provider = EdgeTTSProvider(Cfg())
        assert provider.supports_streaming is False
        # Should fall back to DEFAULT_VOICE without raising NoAudioReceived
        audio = await provider.synthesize("Hello")
        assert len(audio) > 0



    def test_create_sr_provider(self):
        from jarvis.voice.registry import VoiceRegistry
        from jarvis.voice.stt.speech_recognition import SpeechRecognitionProvider

        class Cfg:
            provider = "sr"

        provider = VoiceRegistry().create_stt(Cfg())
        assert isinstance(provider, SpeechRecognitionProvider)

    def test_unknown_tts_raises(self):
        from jarvis.core.exceptions import VoiceConfigError
        from jarvis.voice.registry import VoiceRegistry

        class Cfg:
            provider = "nope"

        with pytest.raises(VoiceConfigError):
            VoiceRegistry().create_tts(Cfg())

    def test_unknown_stt_raises(self):
        from jarvis.core.exceptions import VoiceConfigError
        from jarvis.voice.registry import VoiceRegistry

        class Cfg:
            provider = "nope"

        with pytest.raises(VoiceConfigError):
            VoiceRegistry().create_stt(Cfg())


class TestVoiceManager:
    """Manager mode handling and lifecycle guards (no hardware)."""

    @pytest.mark.asyncio
    async def test_initialize_with_disabled_voice(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.voice.manager import VoiceManager

        config = JarvisConfig()
        config.voice.enabled = False
        manager = VoiceManager(config)
        await manager.initialize()
        assert not manager._initialized

    @pytest.mark.asyncio
    async def test_mode_toggle(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.voice.manager import VoiceManager

        manager = VoiceManager(JarvisConfig())
        manager.set_mode("voice")
        assert manager.mode == "voice"
        assert manager.toggle_mode() == "text"
        assert manager.mode == "text"

    def test_mode_invalid_raises(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.core.exceptions import VoiceError
        from jarvis.voice.manager import VoiceManager

        manager = VoiceManager(JarvisConfig())
        with pytest.raises(VoiceError):
            manager.set_mode("bogus")

    @pytest.mark.asyncio
    async def test_speak_before_initialize_is_noop(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.voice.manager import VoiceManager

        manager = VoiceManager(JarvisConfig())
        await manager.speak("hello")
        await manager.speak_stream("hello")
        assert await manager.listen() == ""
        assert await manager.list_voices() == []


class TestAudioHelpers:
    """Pure-Python PCM/WAV conversion and sentence splitting."""

    def test_pcm_to_wav_wraps_raw_pcm(self):
        import wave

        from jarvis.voice.audio.wav import pcm_to_wav

        pcm = b"\x00\x00\x01\x00\xff\xff\xfe\xff"
        buffer = pcm_to_wav(pcm, sample_rate=16000)
        assert isinstance(buffer, io.BytesIO)
        with wave.open(buffer, "rb") as wav:
            assert wav.getframerate() == 16000
            assert wav.getsampwidth() == 2
            assert wav.getnchannels() == 1
            assert wav.readframes(wav.getnframes()) == pcm

    @pytest.mark.parametrize(
        "buffer,expected_sentences,remaining",
        [
            ("Hello world.", ["Hello world."], ""),
            ("Hi there! How are you? Fine.", ["Hi there!", "How are you?", "Fine."], ""),
            ("Partial sentence without end", [], "Partial sentence without end"),
            ("One. Two. Part", ["One.", "Two."], "Part"),
            ("New\nline sentence.", ["New\nline sentence."], ""),
        ],
    )
    def test_pop_complete_sentences(self, buffer, expected_sentences, remaining):
        from jarvis.ui.tui.app import _pop_complete_sentences

        sentences, leftover = _pop_complete_sentences(buffer)
        assert sentences == expected_sentences
        assert leftover == remaining


class TestWhisperHelpers:
    """Language normalization for whisper models."""

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("en-US", "en"),
            ("en", "en"),
            ("fr-FR", "fr"),
            ("", None),
            ("  ", None),
            (None, None),
        ],
    )
    def test_normalize_language(self, language, expected):
        from jarvis.voice.stt.whisper import WhisperProvider

        assert WhisperProvider._normalize_language(language) == expected


class TestAudioPlayerStream:
    """Audio player stream buffering tests."""

    @pytest.mark.asyncio
    async def test_play_stream_accumulates_bytes(self, monkeypatch):
        from jarvis.voice.audio.player import AudioPlayer

        player = AudioPlayer()
        played_bytes = []

        async def fake_play_bytes(data: bytes) -> None:
            played_bytes.append(data)

        monkeypatch.setattr(player, "play_bytes", fake_play_bytes)

        async def sample_chunk_stream():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        await player.play_stream(sample_chunk_stream())
        assert played_bytes == [b"chunk1chunk2chunk3"]

    def test_decode_returns_none_when_miniaudio_is_none(self, monkeypatch):
        import jarvis.voice.audio.player as player_mod

        monkeypatch.setattr(player_mod, "miniaudio", None)
        player = player_mod.AudioPlayer.__new__(player_mod.AudioPlayer)
        player.sample_rate = 44100
        assert player.decode(b"test audio") is None

    @pytest.mark.asyncio
    async def test_close_handles_sd_is_none(self, monkeypatch):
        import jarvis.voice.audio.player as player_mod

        monkeypatch.setattr(player_mod, "sd", None)
        player = player_mod.AudioPlayer.__new__(player_mod.AudioPlayer)
        await player.close()  # Should not raise AttributeError

    @pytest.mark.asyncio
    async def test_recorder_capture_returns_none_when_sd_is_none(self, monkeypatch):
        import jarvis.voice.audio.recorder as recorder_mod

        monkeypatch.setattr(recorder_mod, "sd", None)
        recorder = recorder_mod.AudioRecorder.__new__(recorder_mod.AudioRecorder)
        assert await recorder.capture() is None

    def test_in_voice_mode_returns_false_when_voice_manager_is_none(self):
        from jarvis.ui.tui.app import _in_voice_mode

        class DummyEngine:
            voice_manager = None

        assert _in_voice_mode(DummyEngine()) is False




