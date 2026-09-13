from pathlib import Path
from types import SimpleNamespace

from src.speech.factory import build_stt_service
from src.speech.stt import LocalWhisperSttService, OpenAiSttService


class _FakeTranscriptions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=" Buenos días, ¿qué tal? ")


class _FakeClient:
    def __init__(self) -> None:
        self.audio = SimpleNamespace(transcriptions=_FakeTranscriptions())


def _settings(**overrides):
    values = dict(
        stt_provider="local_whisper",
        whisper_model="small",
        whisper_language=None,
        audio_cache_dir=".audio_cache",
        openai_api_key=None,
        openai_stt_model="gpt-4o-mini-transcribe",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_openai_cloud_stt_sends_language_and_context_prompt(tmp_path: Path):
    service = OpenAiSttService("secret", model_name="gpt-4o-mini-transcribe")
    fake = _FakeClient()
    service._client = fake
    wav = tmp_path / "sample.wav"
    wav.write_bytes(b"RIFF fake")

    text, language = service._transcribe_wav(
        wav,
        language="es",
        initial_prompt="Viajes, Tenerife, alquiler de coche.",
    )

    assert text == "Buenos días, ¿qué tal?"
    assert language == "es"
    call = fake.audio.transcriptions.calls[0]
    assert call["model"] == "gpt-4o-mini-transcribe"
    assert call["language"] == "es"
    assert "Tenerife" in call["prompt"]
    assert call["file"].name.endswith("sample.wav")


def test_stt_factory_builds_local_or_cloud_provider():
    local = build_stt_service(_settings())
    assert isinstance(local, LocalWhisperSttService)

    cloud = build_stt_service(
        _settings(stt_provider="openai", openai_api_key="secret", openai_stt_model="gpt-4o-transcribe")
    )
    assert isinstance(cloud, OpenAiSttService)
    assert cloud.model_name == "gpt-4o-transcribe"


def test_openai_stt_without_key_is_not_configured():
    assert build_stt_service(_settings(stt_provider="openai", openai_api_key=None)) is None
