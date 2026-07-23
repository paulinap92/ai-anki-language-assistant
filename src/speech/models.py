"""Shared speech-domain models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TtsRequest:
    """One deterministic text-to-speech request."""

    text: str
    language: str
    model: str
    voice: str


@dataclass(frozen=True)
class TtsResult:
    """Generated or reused audio file."""

    path: Path
    provider_name: str
    model: str
    voice: str
    cached: bool


@dataclass(frozen=True)
class TtsDiagnostic:
    """Result of a small TTS provider preflight/diagnostic check."""

    ok: bool
    provider_name: str
    model: str
    voice: str
    api_key_status: str
    auth_status: str
    sample_path: Path | None = None
    error_message: str = ""

    def to_message(self) -> str:
        """Return a compact user-facing diagnostic summary."""
        parts = [
            f"Provider: {self.provider_name}",
            f"API key: {self.api_key_status}",
            f"Auth/generation: {self.auth_status}",
            f"Model: {self.model or 'default'}",
            f"Voice: {self.voice or 'default'}",
        ]
        if self.sample_path:
            parts.append(f"sample: {self.sample_path.name}")
        if self.error_message:
            parts.append(self.error_message)
        return " · ".join(parts)
