"""Local speech-to-text helpers for Conversation Practice.

This module is intentionally small: it records microphone input, writes a
temporary WAV file, and transcribes it with faster-whisper. The GUI still uses
text as the source of truth, so users can edit the transcript before sending it
for feedback.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SttResult:
    """Result returned by a speech-to-text provider."""

    text: str
    provider: str
    model: str
    language: str | None = None


class LocalWhisperSttService:
    """Record microphone audio and transcribe it with faster-whisper.

    Dependencies are imported lazily so the rest of the app can still start even
    when STT packages are not installed yet.
    """

    provider_name = "Local Whisper"

    def __init__(
        self,
        model_name: str = "base",
        language: str | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self.model_name = model_name
        self.language = language or None
        self.sample_rate = sample_rate
        self._stream: Any | None = None
        self._frames: list[Any] = []
        self._model: Any | None = None
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Whether an audio stream is currently recording."""
        return self._is_recording

    def start_recording(self) -> None:
        """Start recording microphone audio into memory."""
        if self._is_recording:
            raise RuntimeError("Recording is already running.")

        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice is not installed. Run: pipenv install sounddevice soundfile faster-whisper"
            ) from exc

        self._frames = []

        def _callback(indata: Any, frames: int, time: Any, status: Any) -> None:
            if status:
                # Keep recording; status is informational for temporary underflows.
                pass
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=_callback,
        )
        self._stream.start()
        self._is_recording = True

    def stop_and_transcribe(self) -> SttResult:
        """Stop recording and transcribe the recorded audio."""
        if not self._is_recording or self._stream is None:
            raise RuntimeError("No recording is running.")

        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._is_recording = False

        if not self._frames:
            raise RuntimeError("No audio was recorded.")

        try:
            import numpy as np  # type: ignore
            import soundfile as sf  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "soundfile/numpy is not installed. Run: pipenv install sounddevice soundfile faster-whisper"
            ) from exc

        audio = np.concatenate(self._frames, axis=0)
        if audio.size == 0:
            raise RuntimeError("No audio was recorded.")

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            sf.write(str(tmp_path), audio, self.sample_rate)
            text, detected_language = self._transcribe_wav(tmp_path)
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        return SttResult(
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            language=detected_language,
        )

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Run: pipenv install faster-whisper sounddevice soundfile"
            ) from exc

        self._model = WhisperModel(
            self.model_name,
            device="cpu",
            compute_type="int8",
        )
        return self._model

    def _transcribe_wav(self, wav_path: Path) -> tuple[str, str | None]:
        model = self._load_model()
        segments, info = model.transcribe(
            str(wav_path),
            language=self.language,
            beam_size=5,
            vad_filter=True,
        )
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip(), getattr(info, "language", None)
