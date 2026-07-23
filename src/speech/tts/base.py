"""Common text-to-speech provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.speech.models import TtsRequest


class TextToSpeechProvider(ABC):
    """Generate an audio file from exact text."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """User-facing provider name."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier."""

    @property
    @abstractmethod
    def default_voice(self) -> str:
        """Default voice identifier."""

    @property
    @abstractmethod
    def models(self) -> list[str]:
        """Suggested model identifiers."""

    @property
    @abstractmethod
    def voices(self) -> list[str]:
        """Suggested voice identifiers."""

    @property
    @abstractmethod
    def output_extension(self) -> str:
        """Generated file extension without a leading dot."""

    @abstractmethod
    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        """Generate speech and write it to ``output_path``."""
