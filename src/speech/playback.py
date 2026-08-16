"""In-app audio playback without opening an external media player."""

from __future__ import annotations

from pathlib import Path
from threading import RLock


class InternalAudioPlayer:
    """Play WAV/MP3 files through sounddevice while keeping sample data alive."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._data = None
        self._path: Path | None = None

    @property
    def current_path(self) -> Path | None:
        return self._path

    def play(self, path: Path) -> None:
        try:
            import sounddevice as sd  # type: ignore
            import soundfile as sf  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "In-app audio playback requires sounddevice and soundfile."
            ) from exc

        path = Path(path)
        if not path.exists() or path.stat().st_size <= 0:
            raise FileNotFoundError(f"Audio file is missing or empty: {path}")
        try:
            data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
        except Exception as exc:
            raise RuntimeError(f"Could not decode audio file for in-app playback: {path.name}") from exc
        if getattr(data, "size", 0) <= 0:
            raise RuntimeError(f"Audio file contains no playable samples: {path.name}")

        with self._lock:
            sd.stop()
            self._data = data
            self._path = path
            # Non-blocking playback keeps Tkinter responsive. self._data keeps the
            # numpy buffer alive until playback is replaced/stopped.
            sd.play(self._data, int(sample_rate), blocking=False)

    def wait(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("In-app audio playback requires sounddevice.") from exc
        sd.wait()

    def stop(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError:
            return
        with self._lock:
            sd.stop()
            self._data = None
            self._path = None
