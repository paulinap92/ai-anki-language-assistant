"""Speech-to-text services for Conversation Practice.

Both local and cloud providers share the same microphone recording flow. The last
WAV recording is always kept for diagnostics, and the resulting transcript stays
editable in the GUI before it is sent to the conversation model.
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


class RecordedSttService:
    """Common microphone recorder used by local and cloud STT providers."""

    provider_name = "Speech-to-text"

    def __init__(
        self,
        model_name: str,
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
        self._is_recording = False
        self._recording_started_at: float | None = None
        self.last_recording_path: Path | None = None
        self.last_recording_duration_seconds: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def recording_duration_seconds(self) -> float:
        if not self._is_recording or self._recording_started_at is None:
            return self.last_recording_duration_seconds
        return max(0.0, time.monotonic() - self._recording_started_at)

    def start_recording(self) -> None:
        if self._is_recording:
            raise RuntimeError("Recording is already running.")

        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice is not installed. Run: pipenv install sounddevice soundfile"
            ) from exc

        input_device = self._select_input_device(sd)
        self._frames = []
        self.last_recording_path = None
        self.last_recording_duration_seconds = 0.0

        def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if status:
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
        if not self._is_recording or self._stream is None:
            raise RuntimeError("No recording is running.")

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
                "soundfile/numpy is not installed. Run: pipenv install sounddevice soundfile numpy"
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

    def _transcribe_wav(
        self,
        wav_path: Path,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> tuple[str, str | None]:
        raise NotImplementedError


class LocalWhisperSttService(RecordedSttService):
    """Transcribe recordings locally with faster-whisper."""

    provider_name = "Local Whisper"

    def __init__(
        self,
        model_name: str = "base",
        language: str | None = None,
        sample_rate: int = 16000,
        cache_dir: str | Path = ".audio_cache",
        stop_tail_seconds: float = 0.8,
    ) -> None:
        super().__init__(model_name, language, sample_rate, cache_dir, stop_tail_seconds)
        self._model: Any | None = None

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


class OpenAiSttService(RecordedSttService):
    """Transcribe recordings with OpenAI's cloud audio transcription endpoint."""

    provider_name = "OpenAI Cloud STT"

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini-transcribe",
        language: str | None = None,
        sample_rate: int = 16000,
        cache_dir: str | Path = ".audio_cache",
        stop_tail_seconds: float = 0.8,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OPENAI_API_KEY is required for OpenAI Cloud STT.")
        super().__init__(model_name, language, sample_rate, cache_dir, stop_tail_seconds)
        self._api_key = api_key.strip()
        self._client: Any | None = None

    def _load_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai is not installed. Run: pipenv install openai sounddevice soundfile"
            ) from exc
        self._client = OpenAI(api_key=self._api_key)
        return self._client

    def _transcribe_wav(
        self,
        wav_path: Path,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> tuple[str, str | None]:
        client = self._load_client()
        prompt = (initial_prompt or "").strip()
        if len(prompt) > 1200:
            prompt = prompt[-1200:]
        request_language = language or self.language
        kwargs: dict[str, Any] = {
            "model": self.model_name,
        }
        if request_language:
            kwargs["language"] = request_language
        if prompt:
            kwargs["prompt"] = prompt
        with wav_path.open("rb") as audio_file:
            result = client.audio.transcriptions.create(file=audio_file, **kwargs)
        text = str(getattr(result, "text", "") or "").strip()
        return text, request_language
