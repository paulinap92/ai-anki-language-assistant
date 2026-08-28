"""Local Piper text-to-speech providers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import wave

from src.speech.models import TtsRequest
from src.speech.tts.base import TextToSpeechProvider


class PiperTtsProvider(TextToSpeechProvider):
    """Generate WAV speech with the optional Python piper-tts package."""

    def __init__(self, model_paths: Path | list[Path]) -> None:
        if isinstance(model_paths, Path):
            model_paths = [model_paths]
        self._model_paths = [Path(path) for path in model_paths]
        if not self._model_paths:
            raise ValueError("Configure at least one Piper voice model path.")
        self._model_path = self._model_paths[0]
        self._voice = None

    @property
    def provider_name(self) -> str:
        return "Piper (local)"

    @property
    def default_model(self) -> str:
        return str(self._model_path)

    @property
    def default_voice(self) -> str:
        return str(self._model_path)

    @property
    def models(self) -> list[str]:
        return [str(path) for path in self._model_paths]

    @property
    def voices(self) -> list[str]:
        return [str(path) for path in self._model_paths]

    @property
    def output_extension(self) -> str:
        return "wav"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "Piper Python package is not installed. Either install piper-tts "
                "or configure PIPER_EXE_PATH for the standalone piper.exe."
            ) from exc
        model_path = Path(request.voice or request.model)
        if not model_path.exists() and request.model:
            model_path = Path(request.model)
        if not model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {model_path}")
        if self._voice is None or model_path != self._model_path:
            self._model_path = model_path
            self._voice = PiperVoice.load(str(model_path))
        with wave.open(str(output_path), "wb") as wav_file:
            self._voice.synthesize_wav(request.text, wav_file)


class PiperExecutableTtsProvider(TextToSpeechProvider):
    """Generate WAV speech with a standalone piper.exe binary."""

    def __init__(self, exe_path: Path, voice_models: list[Path]) -> None:
        self._exe_path = exe_path
        self._voice_models = voice_models
        if not self._voice_models:
            raise ValueError("Configure at least one Piper voice model path.")

    @property
    def provider_name(self) -> str:
        return "Piper Local"

    @property
    def default_model(self) -> str:
        return str(self._voice_models[0])

    @property
    def default_voice(self) -> str:
        return str(self._voice_models[0])

    @property
    def models(self) -> list[str]:
        return [str(path) for path in self._voice_models]

    @property
    def voices(self) -> list[str]:
        return [str(path) for path in self._voice_models]

    @property
    def output_extension(self) -> str:
        return "wav"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        exe_path = Path(self._exe_path)
        model_path = Path(request.voice or request.model)
        if not model_path.exists() and request.model:
            model_path = Path(request.model)
        if not exe_path.exists():
            raise FileNotFoundError(f"Piper executable not found: {exe_path}")
        if not model_path.exists():
            raise FileNotFoundError(f"Piper voice model not found: {model_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(exe_path),
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        proc = subprocess.run(
            command,
            input=request.text,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "unknown Piper error").strip()
            raise RuntimeError(f"Piper failed: {detail}")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Piper did not create a WAV file.")
