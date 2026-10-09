"""In-app audio playback with explicit output selection and safe fallback."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import sys
from threading import RLock, Lock

LOGGER = logging.getLogger(__name__)


class AudioPlaybackError(RuntimeError):
    """A playback failure whose message is safe to show in the UI."""


@dataclass(frozen=True)
class OutputDevice:
    index: int
    name: str
    host_api: str

    @property
    def label(self) -> str:
        # Indices distinguish duplicate names in this session, but are not saved.
        return f"{self.name} — {self.host_api} [{self.index}]"


@dataclass(frozen=True)
class PlaybackResult:
    device: OutputDevice
    used_fallback: bool = False


def list_output_devices() -> list[OutputDevice]:
    """List output-capable devices without importing audio modules at startup."""
    try:
        import sounddevice as sd
        hosts = sd.query_hostapis()
        return [
            OutputDevice(i, device["name"], hosts[device["hostapi"]]["name"])
            for i, device in enumerate(sd.query_devices())
            if device["max_output_channels"] > 0
        ]
    except ImportError as exc:
        raise AudioPlaybackError("Audio playback requires sounddevice and soundfile.") from exc
    except Exception as exc:
        LOGGER.exception("Could not enumerate audio outputs")
        raise AudioPlaybackError(
            "Could not list audio outputs. Check your speakers or headphones, then click Refresh devices."
        ) from exc


def _output_candidates(sd, devices, name: str, host_api: str) -> list[OutputDevice]:
    candidates: list[OutputDevice] = []

    def add(index) -> None:
        device = next((d for d in devices if d.index == index), None)
        if device is not None and device not in candidates:
            candidates.append(device)

    matches = [d for d in devices if d.name == name and d.host_api == host_api]
    # Do not guess between indistinguishable endpoints after a restart.
    if name and len(matches) == 1:
        add(matches[0].index)
    if sys.platform.startswith("win"):
        for host in sd.query_hostapis():
            if host["name"] == "Windows WASAPI":
                add(host["default_output_device"])
    add(sd.default.device[1])
    return candidates


class InternalAudioPlayer:
    """Play WAV/MP3 files; callers may run decoding/opening in a worker."""

    # sd.play/stop/wait operate on one global convenience stream, even across
    # the preview and conversation player instances.
    _lock = RLock()
    _request_lock = Lock()
    _request_serial = 0

    def __init__(self) -> None:
        self._data = None
        self._path: Path | None = None
        self._device_name = ""
        self._host_api = ""

    @classmethod
    def reserve_request(cls) -> int:
        with cls._request_lock:
            cls._request_serial += 1
            return cls._request_serial

    @classmethod
    def is_current_request(cls, request_id: int) -> bool:
        return request_id == cls._request_serial

    def set_output_device(self, name: str = "", host_api: str = "") -> None:
        self._device_name, self._host_api = name, host_api

    @property
    def current_path(self) -> Path | None:
        return self._path

    def play(self, path: Path, *, request_id: int | None = None) -> PlaybackResult | None:
        request_id = self.reserve_request() if request_id is None else request_id
        name, host_api = self._device_name, self._host_api
        try:
            import sounddevice as sd
            import soundfile as sf
        except ImportError as exc:
            raise AudioPlaybackError("Audio playback requires sounddevice and soundfile.") from exc

        path = Path(path)
        if not path.exists() or path.stat().st_size <= 0:
            raise AudioPlaybackError("The audio file is missing or empty. Generate the audio again.")
        try:
            data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
        except Exception as exc:
            raise AudioPlaybackError("Could not read this audio file. Generate the audio again.") from exc
        if getattr(data, "size", 0) <= 0:
            raise AudioPlaybackError("The audio file contains no playable samples.")

        devices = list_output_devices()
        candidates = _output_candidates(sd, devices, name, host_api)
        last_error = None
        with self._lock:
            if request_id != self._request_serial:
                return None
            sd.stop()
            self._data = None
            self._path = None
            for device in candidates:
                if request_id != self._request_serial:
                    return None
                extra = (
                    sd.WasapiSettings(exclusive=False, auto_convert=True)
                    if device.host_api == "Windows WASAPI" else None
                )
                try:
                    settings = dict(device=device.index, samplerate=int(sample_rate),
                                    channels=data.shape[1], dtype="float32", extra_settings=extra)
                    sd.check_output_settings(**settings)
                    sd.play(data, int(sample_rate), device=device.index,
                            extra_settings=extra, blocking=False)
                except (sd.PortAudioError, ValueError) as exc:
                    last_error = exc
                    LOGGER.warning("Audio output failed: device=%s host_api=%s rate=%s channels=%s",
                                   device.name, device.host_api, sample_rate, data.shape[1], exc_info=True)
                    sd.stop()
                    continue
                self._data, self._path = data, path
                fallback = bool(name and (device.name != name or device.host_api != host_api))
                fallback = fallback or device != candidates[0]
                return PlaybackResult(device, fallback)

        raise AudioPlaybackError(
            "Audio is ready, but playback could not start. Check your speakers or headphones "
            "and select an output device in Speech & Audio → Output device."
        ) from last_error

    def wait(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise AudioPlaybackError("Audio playback requires sounddevice.") from exc
        sd.wait()

    def stop(self, *, request_id: int | None = None) -> None:
        request_id = self.reserve_request() if request_id is None else request_id
        try:
            import sounddevice as sd
        except ImportError:
            return
        with self._lock:
            if not self.is_current_request(request_id):
                return
            sd.stop()
            self._data = None
            self._path = None
