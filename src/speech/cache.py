"""Deterministic local cache for generated speech files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.speech.models import TtsRequest


class AudioCache:
    """Map speech request parameters to stable local file paths."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, provider_name: str, request: TtsRequest, extension: str) -> Path:
        """Return a stable filename for the complete synthesis configuration."""
        payload = {
            "provider": provider_name.casefold(),
            "text": " ".join(request.text.split()),
            "language": request.language.casefold(),
            "model": request.model,
            "voice": request.voice,
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        safe_extension = extension.lstrip(".").casefold()
        return self._directory / f"anki_tts_{digest}.{safe_extension}"
