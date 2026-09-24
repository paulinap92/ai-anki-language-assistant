"""Factory for configured speech-to-text services."""

from __future__ import annotations

from src.core.config import Settings
from src.speech.stt import GroqSttService, LocalWhisperSttService, OpenAiSttService, RecordedSttService


def build_stt_service(settings: Settings) -> RecordedSttService | None:
    """Build the configured STT provider without loading heavy models eagerly."""
    provider = (settings.stt_provider or "local_whisper").strip().casefold()
    if provider in {"local_whisper", "whisper", "faster_whisper", "local"}:
        return LocalWhisperSttService(
            model_name=settings.whisper_model,
            language=settings.whisper_language,
            cache_dir=settings.audio_cache_dir,
        )
    if provider in {"openai", "openai_cloud", "openai_stt", "cloud_openai"}:
        if not settings.openai_api_key:
            return None
        return OpenAiSttService(
            api_key=settings.openai_api_key,
            model_name=settings.openai_stt_model,
            language=settings.whisper_language,
            cache_dir=settings.audio_cache_dir,
        )
    if provider in {"groq", "groq_cloud", "groq_stt", "cloud_groq"}:
        if not settings.groq_api_key:
            return None
        return GroqSttService(
            api_key=settings.groq_api_key,
            model_name=settings.groq_stt_model,
            language=settings.whisper_language,
            cache_dir=settings.audio_cache_dir,
        )
    return None
