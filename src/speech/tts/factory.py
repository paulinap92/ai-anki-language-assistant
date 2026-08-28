"""Factory for configured text-to-speech providers."""

from __future__ import annotations

from pathlib import Path

from src.core.config import Settings
from src.speech.tts.base import TextToSpeechProvider
from src.speech.voice_library import installed_piper_models


def build_tts_providers(settings: Settings) -> dict[str, TextToSpeechProvider]:
    """Build TTS providers allowed by the selected setup profile.

    Imports are lazy so local-only users do not need cloud SDK packages.
    """
    providers: dict[str, TextToSpeechProvider] = {}
    mode = (settings.setup_mode or "hybrid").casefold()
    allow_local = mode in {"local", "hybrid"}
    allow_cloud = mode in {"api", "hybrid"}

    if allow_cloud and settings.openai_api_key:
        from src.speech.tts.openai_tts import OpenAiTtsProvider

        provider = OpenAiTtsProvider(
            settings.openai_api_key,
            settings.openai_tts_model,
            settings.openai_tts_voice,
        )
        providers[provider.provider_name] = provider

    if allow_cloud and settings.gemini_api_key:
        from src.speech.tts.gemini_tts import GeminiTtsProvider

        provider = GeminiTtsProvider(
            settings.gemini_api_key,
            settings.gemini_tts_model,
            settings.gemini_tts_voice,
        )
        providers[provider.provider_name] = provider

    if allow_local:
        from src.speech.tts.piper import PiperExecutableTtsProvider, PiperTtsProvider

        piper_voice_candidates = [
            settings.piper_voice_en,
            settings.piper_voice_es,
            settings.piper_voice_pl,
            settings.piper_model_path,
        ]
        piper_voice_paths: list[Path] = []
        for candidate in piper_voice_candidates:
            if candidate:
                path = Path(candidate)
                if path not in piper_voice_paths:
                    piper_voice_paths.append(path)
        for path in installed_piper_models():
            if path not in piper_voice_paths:
                piper_voice_paths.append(path)

        if settings.piper_exe_path and piper_voice_paths:
            provider = PiperExecutableTtsProvider(
                Path(settings.piper_exe_path),
                piper_voice_paths,
            )
            providers[provider.provider_name] = provider
        elif piper_voice_paths:
            provider = PiperTtsProvider(piper_voice_paths)
            providers[provider.provider_name] = provider

    if allow_cloud and settings.elevenlabs_api_key:
        from src.speech.tts.elevenlabs import ElevenLabsTtsProvider

        provider = ElevenLabsTtsProvider(
            settings.elevenlabs_api_key,
            settings.elevenlabs_tts_model,
            settings.elevenlabs_voice_id,
        )
        providers[provider.provider_name] = provider

    return providers
