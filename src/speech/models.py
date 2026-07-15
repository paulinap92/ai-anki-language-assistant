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
