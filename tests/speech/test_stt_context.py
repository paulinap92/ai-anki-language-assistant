from pathlib import Path
from types import SimpleNamespace

from src.speech.stt import LocalWhisperSttService


class _Segment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeWhisperModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def transcribe(self, path: str, **kwargs: object):
        self.calls.append((path, kwargs))
        return [_Segment(" Land Rover 109 "), _Segment(" está homologado. ")], SimpleNamespace(language="es")


def test_transcription_uses_language_context_and_vad(tmp_path: Path):
    service = LocalWhisperSttService(model_name="small", language=None)
    fake_model = _FakeWhisperModel()
    service._model = fake_model
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(b"placeholder")

    text, language = service._transcribe_wav(
        wav_path,
        language="es",
        initial_prompt="Coches clásicos. Land Rover 109, ITV, homologación.",
    )

    assert text == "Land Rover 109 está homologado."
    assert language == "es"
    _path, kwargs = fake_model.calls[0]
    assert kwargs["language"] == "es"
    assert kwargs["vad_filter"] is True
    assert kwargs["condition_on_previous_text"] is False
    assert "Land Rover 109" in str(kwargs["initial_prompt"])


def test_transcription_prompt_is_bounded(tmp_path: Path):
    service = LocalWhisperSttService(model_name="small", language="es")
    fake_model = _FakeWhisperModel()
    service._model = fake_model
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(b"placeholder")

    long_prompt = "x" * 2000
    service._transcribe_wav(wav_path, initial_prompt=long_prompt)

    _path, kwargs = fake_model.calls[0]
    assert len(str(kwargs["initial_prompt"])) == 1200
