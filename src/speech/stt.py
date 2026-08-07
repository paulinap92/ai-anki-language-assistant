"""Local speech-to-text helpers for Conversation Practice.

This module records microphone input, keeps the last WAV file for diagnostics,
and transcribes it with faster-whisper. The GUI still uses text as the source of
truth, so users can edit the transcript before sending it for feedback.
"""

from __future__ import annotations

import time
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
    audio_path: Path | None = None
    duration_seconds: float = 0.0


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
        cache_dir: str | Path = ".audio_cache",
        stop_tail_seconds: float = 0.8,
    ) -> None:
        self.model_name = model_name
        self.language = language or None
        self.sample_rate = sample_rate
        self.cache_dir = Path(cache_dir)
        self.stop_tail_seconds = stop_tail_seconds
        self._stream: Any | None = None
        self._frames: list[Any] = []
        self._model: Any | None = None
        self._is_recording = False
        self._recording_started_at: float | None = None
        self.last_recording_path: Path | None = None
        self.last_recording_duration_seconds: float = 0.0

    @property
    def is_recording(self) -> bool:
        """Whether an audio stream is currently recording."""
        return self._is_recording

    @property
    def recording_duration_seconds(self) -> float:
        """Current recording duration for GUI status display."""
        if not self._is_recording or self._recording_started_at is None:
            return self.last_recording_duration_seconds
        return max(0.0, time.monotonic() - self._recording_started_at)

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

        input_device = self._select_input_device(sd)
        self._frames = []
        self.last_recording_path = None
        self.last_recording_duration_seconds = 0.0

        def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if status:
                # Keep recording; status is informational for temporary underflows.
                pass
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            device=input_device,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=_callback,
        )
        self._stream.start()
        self._recording_started_at = time.monotonic()
        self._is_recording = True

    @staticmethod
    def _select_input_device(sd: Any) -> int | None:
        """Return a usable input device or raise a friendly no-microphone error."""
        try:
            default_device = sd.default.device
            default_input = default_device[0] if isinstance(default_device, (list, tuple)) else default_device
            if default_input is not None and int(default_input) >= 0:
                info = sd.query_devices(int(default_input), "input")
                if int(info.get("max_input_channels", 0)) > 0:
                    return int(default_input)
        except Exception:
            pass

        try:
            devices = sd.query_devices()
        except Exception as exc:
            raise RuntimeError(
                "No microphone/input device detected. Connect or enable a microphone, then try again."
            ) from exc

        for index, device in enumerate(devices):
            try:
                if int(device.get("max_input_channels", 0)) > 0:
                    return index
            except Exception:
                continue
        raise RuntimeError(
            "No microphone/input device detected. Connect or enable a microphone, then try again."
        )

    def stop_and_transcribe(
        self,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> SttResult:
        """Stop recording, keep last_recording.wav, and transcribe it.

        ``language`` and ``initial_prompt`` may be supplied by Conversation Practice so
        Whisper is biased toward the selected language, current topic, proper names and
        active flashcard vocabulary instead of relying on automatic detection alone.
        """
        if not self._is_recording or self._stream is None:
            raise RuntimeError("No recording is running.")

        # Give the audio callback a short tail so the final words are not lost.
        if self.stop_tail_seconds > 0:
            time.sleep(self.stop_tail_seconds)

        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._is_recording = False
        if self._recording_started_at is not None:
            self.last_recording_duration_seconds = max(0.0, time.monotonic() - self._recording_started_at)
        self._recording_started_at = None

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

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        wav_path = self.cache_dir / "last_recording.wav"
        sf.write(str(wav_path), audio, self.sample_rate)
        self.last_recording_path = wav_path
        text, detected_language = self._transcribe_wav(
            wav_path,
            initial_prompt=initial_prompt,
            language=language,
        )

        return SttResult(
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            language=detected_language,
            audio_path=wav_path,
            duration_seconds=self.last_recording_duration_seconds,
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

    def _transcribe_wav(
        self,
        wav_path: Path,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> tuple[str, str | None]:
        model = self._load_model()
        prompt = (initial_prompt or "").strip()
        # faster-whisper accepts a free-text initial prompt. Keep it bounded so a long
        # conversation history cannot dominate the acoustic transcription.
        if len(prompt) > 1200:
            prompt = prompt[-1200:]
        segments, info = model.transcribe(
            str(wav_path),
            language=language or self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 350},
            condition_on_previous_text=False,
            initial_prompt=prompt or None,
        )
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip(), getattr(info, "language", None)
