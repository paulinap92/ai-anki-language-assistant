"""Factory for configured text-to-speech providers."""

from __future__ import annotations

from pathlib import Path

from src.core.config import Settings
from src.speech.tts.base import TextToSpeechProvider
from src.speech.tts.elevenlabs import ElevenLabsTtsProvider
from src.speech.tts.gemini_tts import GeminiTtsProvider
from src.speech.tts.openai_tts import OpenAiTtsProvider
from src.speech.tts.piper import PiperTtsProvider


def build_tts_providers(settings: Settings) -> dict[str, TextToSpeechProvider]:
    """Build only providers whose credentials or local model are configured."""
    providers: dict[str, TextToSpeechProvider] = {}
    if settings.elevenlabs_api_key:
        provider = ElevenLabsTtsProvider(
            settings.elevenlabs_api_key,
            settings.elevenlabs_tts_model,
            settings.elevenlabs_voice_id,
        )
        providers[provider.provider_name] = provider
    if settings.openai_api_key:
        provider = OpenAiTtsProvider(
            settings.openai_api_key,
            settings.openai_tts_model,
            settings.openai_tts_voice,
        )
        providers[provider.provider_name] = provider
    if settings.gemini_api_key:
        provider = GeminiTtsProvider(
            settings.gemini_api_key,
            settings.gemini_tts_model,
            settings.gemini_tts_voice,
        )
        providers[provider.provider_name] = provider
    if settings.piper_model_path:
        provider = PiperTtsProvider(Path(settings.piper_model_path))
        providers[provider.provider_name] = provider
    return providers
