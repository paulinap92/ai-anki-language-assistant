"""Local Piper text-to-speech provider."""

from __future__ import annotations

from pathlib import Path
import wave

from src.speech.models import TtsRequest
from src.speech.tts.base import TextToSpeechProvider


class PiperTtsProvider(TextToSpeechProvider):
    """Generate WAV speech locally with a configured Piper voice model."""

    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._voice = None

    @property
    def provider_name(self) -> str:
        return "Piper (local)"

    @property
    def default_model(self) -> str:
        return str(self._model_path)

    @property
    def default_voice(self) -> str:
        return self._model_path.stem

    @property
    def models(self) -> list[str]:
        return [str(self._model_path)]

    @property
    def voices(self) -> list[str]:
        return [self._model_path.stem]

    @property
    def output_extension(self) -> str:
        return "wav"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "Piper is not installed. Install the optional piper-tts package."
            ) from exc
        model_path = Path(request.model)
        if not model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {model_path}")
        if self._voice is None or model_path != self._model_path:
            self._model_path = model_path
            self._voice = PiperVoice.load(str(model_path))
        with wave.open(str(output_path), "wb") as wav_file:
            self._voice.synthesize_wav(request.text, wav_file)
