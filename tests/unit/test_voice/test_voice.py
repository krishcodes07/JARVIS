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
        from jarvis.voice.tts.edge_tts import EdgeTTSProvider

        class Cfg:
            provider = "edge_tts"
            voice = "invalid-voice-name-xyz"

        provider = EdgeTTSProvider(Cfg())
        assert provider.supports_streaming is True
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
        import jarvis.voice.audio.player as player_mod
        from jarvis.voice.audio.player import AudioPlayer

        monkeypatch.setattr(player_mod, "_pyaudio", None)
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
        import threading

        import jarvis.voice.audio.player as player_mod

        monkeypatch.setattr(player_mod, "sd", None)
        player = player_mod.AudioPlayer.__new__(player_mod.AudioPlayer)
        player._stop_event = threading.Event()
        await player.close()  # Should not raise AttributeError

    @pytest.mark.asyncio
    async def test_recorder_capture_returns_none_when_sd_is_none(self, monkeypatch):
        import jarvis.voice.audio.recorder as recorder_mod

        monkeypatch.setattr(recorder_mod, "sd", None)
        recorder = recorder_mod.AudioRecorder.__new__(recorder_mod.AudioRecorder)
        assert await recorder.capture() is None


class TestStripMarkdownForSpeech:
    """Tests for stripping markdown formatting and thinking/reasoning blocks for TTS."""

    def test_strip_basic_think_block(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "<think>The user wants to know the time.</think>It is 4:30 PM."
        assert strip_markdown_for_speech(raw) == "It is 4:30 PM."

    def test_strip_multiline_think_block(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = (
            "<think>\n"
            "1. Analyze user request\n"
            "2. Retrieve current system status\n"
            "</think>\n"
            "All systems are functioning normally."
        )
        assert strip_markdown_for_speech(raw) == "All systems are functioning normally."

    def test_strip_salted_think_tags(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "<think:6124c78e>Analyzing weather data for Nainital</think:6124c78e>The sky is clear today."
        assert strip_markdown_for_speech(raw) == "The sky is clear today."

    def test_strip_thought_and_reasoning_tags(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw1 = "<thought>Thinking deeply about this question...</thought>Here is the answer."
        raw2 = "<reasoning>Step by step breakdown</reasoning>Done."
        assert strip_markdown_for_speech(raw1) == "Here is the answer."
        assert strip_markdown_for_speech(raw2) == "Done."

    def test_strip_multiple_think_blocks(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "<think>First thought</think>Part 1. <think>Second thought</think>Part 2."
        assert strip_markdown_for_speech(raw) == "Part 1. Part 2."

    def test_strip_unclosed_think_block(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "<think>Still processing the request..."
        assert strip_markdown_for_speech(raw) == ""

    def test_strip_think_block_only(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "<think>Searching database...</think>"
        assert strip_markdown_for_speech(raw) == ""

    def test_strip_markdown_syntax(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = (
            "<think>Analyzing</think>\n"
            "# Main Header\n"
            "Here is **bold** text, *italic* text, and `inline code`.\n"
            "- Item 1\n"
            "- Item 2\n"
            "[Link Text](https://example.com)\n"
            "```python\nprint('code')\n```"
        )
        cleaned = strip_markdown_for_speech(raw)
        assert "<think>" not in cleaned
        assert "Analyzing" not in cleaned
        assert "#" not in cleaned
        assert "**" not in cleaned
        assert "print('code')" not in cleaned
        assert "Main Header" in cleaned
        assert "bold text" in cleaned
        assert "inline code" in cleaned
        assert "Link Text" in cleaned

    def test_strip_emojis(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        raw = "Hello! 👋 I am JARVIS 🤖. How can I help you today? 😊🚀"
        cleaned = strip_markdown_for_speech(raw)
        assert cleaned == "Hello! I am JARVIS. How can I help you today?"

    def test_empty_string(self):
        from jarvis.voice.utils import strip_markdown_for_speech

        assert strip_markdown_for_speech("") == ""
        assert strip_markdown_for_speech("   ") == ""


class TestMaxSpeakCharacters:
    """Tests for max_speak_characters config and truncation."""

    def test_voice_config_max_characters_default(self):
        from jarvis.core.config import VoiceConfig

        cfg = VoiceConfig()
        assert cfg.max_speak_characters == 10000

    def test_voice_config_aliases(self):
        from jarvis.core.config import VoiceConfig

        cfg1 = VoiceConfig.model_validate({"max_characters": 500})
        assert cfg1.max_speak_characters == 500

        cfg2 = VoiceConfig.model_validate({"max_speak_chars": 2500})
        assert cfg2.max_speak_characters == 2500

        cfg3 = VoiceConfig.model_validate({"max_speak_characters": 0})
        assert cfg3.max_speak_characters == 0

    def test_voice_manager_truncation(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.voice.manager import VoiceManager

        cfg = JarvisConfig()
        cfg.voice.max_speak_characters = 50
        vm = VoiceManager(cfg)

        short_text = "This is short."
        assert vm._truncate_for_speech(short_text) == short_text

        long_text = "A" * 120
        truncated = vm._truncate_for_speech(long_text)
        assert len(truncated) == 50

    def test_voice_manager_unlimited(self):
        from jarvis.core.config import JarvisConfig
        from jarvis.voice.manager import VoiceManager

        cfg = JarvisConfig()
        cfg.voice.max_speak_characters = 0
        vm = VoiceManager(cfg)

        long_text = "A" * 5000
        assert vm._truncate_for_speech(long_text) == long_text


class TestEdgeTTSChunking:
    """Tests for multi-paragraph text chunking in Edge TTS."""

    def test_short_text_single_chunk(self):
        from jarvis.voice.tts.edge_tts import _chunk_text_for_edge_tts

        text = "Hello world! This is a simple response."
        chunks = _chunk_text_for_edge_tts(text, max_chars=600)
        assert chunks == [text]

    def test_multi_paragraph_chunking(self):
        from jarvis.voice.tts.edge_tts import _chunk_text_for_edge_tts

        p1 = "First paragraph with introductory information and helpful details."
        p2 = "Second paragraph with deeper explanations and more text."
        p3 = "Third paragraph with concluding notes and closing guidance."
        full_text = f"{p1}\n\n{p2}\n\n{p3}"

        chunks = _chunk_text_for_edge_tts(full_text, max_chars=100)
        assert len(chunks) == 3
        assert chunks[0] == p1
        assert chunks[1] == p2
        assert chunks[2] == p3


class TestElevenLabsProvider:
    """Unit tests for ElevenLabsProvider streaming and voice resolution."""

    def test_missing_api_key_raises_auth_error(self, monkeypatch):
        from jarvis.core.exceptions import VoiceAuthError
        from jarvis.voice.tts.elevenlabs import ElevenLabsProvider

        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        class Cfg:
            provider = "elevenlabs"

        with pytest.raises(VoiceAuthError):
            ElevenLabsProvider(Cfg())

    @pytest.mark.asyncio
    async def test_stream_calls_text_to_speech_stream(self, monkeypatch):
        from jarvis.voice.tts.elevenlabs import ElevenLabsProvider

        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-123")

        class Cfg:
            provider = "elevenlabs"
            voice = "21m00Tcm4TlvDq8ikWAM"
            model = "eleven_multilingual_v2"
            output_format = "mp3_44100_128"
            optimize_streaming_latency = 2

        provider = ElevenLabsProvider(Cfg())
        assert provider.supports_streaming is True

        mock_chunks = [b"chunk1", b"chunk2", b"chunk3"]

        async def fake_stream(**kwargs):
            assert kwargs["voice_id"] == "21m00Tcm4TlvDq8ikWAM"
            assert kwargs["text"] == "Hello JARVIS"
            assert kwargs["optimize_streaming_latency"] == 2
            for c in mock_chunks:
                yield c

        provider._client.text_to_speech.stream = fake_stream

        collected = []
        async for chunk in provider.stream("Hello JARVIS"):
            collected.append(chunk)

        assert collected == mock_chunks

    @pytest.mark.asyncio
    async def test_resolve_voice_by_name_and_fallback(self, monkeypatch):
        from jarvis.voice.base import VoiceInfo
        from jarvis.voice.tts.elevenlabs import ElevenLabsProvider

        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-123")

        class Cfg:
            provider = "elevenlabs"
            voice = "en-US-JennyNeural"  # Default edge-tts leftover

        provider = ElevenLabsProvider(Cfg())

        # Mock list_voices
        async def fake_list_voices():
            return [
                VoiceInfo(id="rachel_id_123", name="Rachel"),
                VoiceInfo(id="adam_id_456", name="Adam"),
            ]

        provider.list_voices = fake_list_voices

        # 1. Fallback for edge_tts placeholder "en-US-JennyNeural" -> first voice
        resolved = await provider._resolve_voice(None)
        assert resolved == "rachel_id_123"

        # 2. Resolving by friendly name "Adam"
        resolved_name = await provider._resolve_voice("Adam")
        assert resolved_name == "adam_id_456"

        # 3. Direct ID
        resolved_id = await provider._resolve_voice("custom_voice_id_789")
        assert resolved_id == "custom_voice_id_789"








