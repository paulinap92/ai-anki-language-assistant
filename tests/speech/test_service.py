from pathlib import Path

from src.speech.models import TtsRequest
from src.speech.service import SpeechService
from src.speech.tts.base import TextToSpeechProvider


class FakeProvider(TextToSpeechProvider):
    calls = 0
    @property
    def provider_name(self): return "Fake"
    @property
    def default_model(self): return "fake-model"
    @property
    def default_voice(self): return "fake-voice"
    @property
    def models(self): return [self.default_model]
    @property
    def voices(self): return [self.default_voice]
    @property
    def output_extension(self): return "mp3"
    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        self.calls += 1
        output_path.write_bytes(b"audio")


def test_service_reuses_cached_audio(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = SpeechService({"Fake": provider}, tmp_path)
    first = service.generate("Fake", "Hello", "English", "", "")
    second = service.generate("Fake", "Hello", "English", "", "")
    assert not first.cached
    assert second.cached
    assert provider.calls == 1


def test_service_diagnose_provider_success(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = SpeechService({"Fake": provider}, tmp_path)

    diagnostic = service.diagnose_provider("Fake", "English", "", "")

    assert diagnostic.ok is True
    assert diagnostic.auth_status == "OK"
    assert diagnostic.sample_path is not None
    assert diagnostic.sample_path.exists()
    assert "Provider: Fake" in diagnostic.to_message()


def test_service_diagnose_unknown_provider(tmp_path: Path) -> None:
    service = SpeechService({}, tmp_path)

    diagnostic = service.diagnose_provider("Missing", "English", "", "")

    assert diagnostic.ok is False
    assert "Unknown TTS provider" in diagnostic.error_message
