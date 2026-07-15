"""Application service for cached text-to-speech generation."""

from __future__ import annotations

from pathlib import Path

from src.speech.cache import AudioCache
from src.speech.models import TtsRequest, TtsResult
from src.speech.tts.base import TextToSpeechProvider


class SpeechService:
    """Coordinate configured TTS providers and deterministic caching."""

    def __init__(
        self,
        providers: dict[str, TextToSpeechProvider],
        cache_directory: Path,
    ) -> None:
        self._providers = providers
        self._cache = AudioCache(cache_directory)

    @property
    def providers(self) -> dict[str, TextToSpeechProvider]:
        return self._providers

    def generate(
        self,
        provider_name: str,
        text: str,
        language: str,
        model: str,
        voice: str,
    ) -> TtsResult:
        """Generate or reuse audio for an exact synthesis configuration."""
        clean_text = " ".join(text.split())
        if not clean_text:
            raise ValueError("Cannot generate audio from empty text.")
        try:
            provider = self._providers[provider_name]
        except KeyError as exc:
            raise ValueError(f"Unknown TTS provider: {provider_name}") from exc
        request = TtsRequest(
            text=clean_text,
            language=language,
            model=model.strip() or provider.default_model,
            voice=voice.strip() or provider.default_voice,
        )
        path = self._cache.path_for(
            provider.provider_name, request, provider.output_extension
        )
        cached = path.exists() and path.stat().st_size > 0
        if not cached:
            provider.synthesize(request, path)
        return TtsResult(
            path=path,
            provider_name=provider.provider_name,
            model=request.model,
            voice=request.voice,
            cached=cached,
        )
