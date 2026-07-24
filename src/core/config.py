"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.domain.languages import normalize_language


load_dotenv(override=True)


def _clean_env_value(value: str | None) -> str | None:
    """Return a real environment value or None for empty/placeholder values."""
    if value is None:
        return None
    cleaned = value.strip().strip('"').strip("'")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    placeholder_markers = (
        "your_",
        "insert_",
        "paste_",
        "change_me",
        "changeme",
        "xxx",
        "example",
        "placeholder",
    )
    if lowered in {"none", "null", "todo"}:
        return None
    if any(marker in lowered for marker in placeholder_markers):
        return None
    return cleaned


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    gemini_api_key: str | None
    gemini_model: str
    openai_api_key: str | None
    openai_model: str
    anthropic_api_key: str | None
    claude_model: str
    anki_connect_url: str
    anki_deck_name: str
    default_target_language: str
    elevenlabs_api_key: str | None
    elevenlabs_tts_model: str
    elevenlabs_voice_id: str
    openai_tts_model: str
    openai_tts_voice: str
    gemini_tts_model: str
    gemini_tts_voice: str
    piper_model_path: str | None
    piper_exe_path: str | None
    piper_voice_en: str | None
    piper_voice_es: str | None
    piper_voice_pl: str | None
    ollama_base_url: str
    ollama_model: str | None
    audio_cache_dir: str
    stt_provider: str
    whisper_model: str
    whisper_language: str | None


def get_settings() -> Settings:
    """Load settings from environment variables.

    Returns:
        Application settings.

    Raises:
        ValueError: If no AI provider API key is configured.
    """
    gemini_api_key = _clean_env_value(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    openai_api_key = _clean_env_value(os.getenv("OPENAI_API_KEY"))
    anthropic_api_key = _clean_env_value(os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"))

    ollama_model = _clean_env_value(os.getenv("OLLAMA_MODEL"))

    if not gemini_api_key and not openai_api_key and not anthropic_api_key and not ollama_model:
        raise ValueError(
            "Configure at least one AI provider in .env: GEMINI_API_KEY, "
            "OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_MODEL for local Ollama."
        )

    return Settings(
        gemini_api_key=gemini_api_key,
        gemini_model=_clean_env_value(os.getenv("GEMINI_MODEL")) or "gemini-2.5-flash",
        openai_api_key=openai_api_key,
        openai_model=_clean_env_value(os.getenv("OPENAI_MODEL")) or "gpt-4.1-mini",
        anthropic_api_key=anthropic_api_key,
        claude_model=_clean_env_value(os.getenv("CLAUDE_MODEL")) or "claude-haiku-4-5",
        anki_connect_url=os.getenv("ANKI_CONNECT_URL", "http://localhost:8765"),
        anki_deck_name=os.getenv("ANKI_DECK_NAME", "AI Vocabulary"),
        default_target_language=normalize_language(
            os.getenv("DEFAULT_TARGET_LANGUAGE", "English")
        ),
        elevenlabs_api_key=_clean_env_value(os.getenv("ELEVENLABS_API_KEY")),
        elevenlabs_tts_model=_clean_env_value(os.getenv("ELEVENLABS_TTS_MODEL")) or "eleven_flash_v2_5",
        elevenlabs_voice_id=_clean_env_value(os.getenv("ELEVENLABS_VOICE_ID")) or "JBFqnCBsd6RMkjVDRZzb",
        openai_tts_model=_clean_env_value(os.getenv("OPENAI_TTS_MODEL")) or "gpt-4o-mini-tts",
        openai_tts_voice=_clean_env_value(os.getenv("OPENAI_TTS_VOICE")) or "coral",
        gemini_tts_model=_clean_env_value(os.getenv("GEMINI_TTS_MODEL")) or "gemini-3.1-flash-tts-preview",
        gemini_tts_voice=_clean_env_value(os.getenv("GEMINI_TTS_VOICE")) or "Kore",
        piper_model_path=_clean_env_value(os.getenv("PIPER_MODEL_PATH") or os.getenv("PIPER_VOICE_PATH")),
        piper_exe_path=_clean_env_value(os.getenv("PIPER_EXE_PATH")),
        piper_voice_en=_clean_env_value(os.getenv("PIPER_VOICE_EN")),
        piper_voice_es=_clean_env_value(os.getenv("PIPER_VOICE_ES")),
        piper_voice_pl=_clean_env_value(os.getenv("PIPER_VOICE_PL")),
        ollama_base_url=_clean_env_value(os.getenv("OLLAMA_BASE_URL")) or "http://localhost:11434",
        ollama_model=ollama_model,
        audio_cache_dir=_clean_env_value(os.getenv("AUDIO_CACHE_DIR")) or ".audio_cache",
        stt_provider=_clean_env_value(os.getenv("STT_PROVIDER")) or "local_whisper",
        whisper_model=_clean_env_value(os.getenv("WHISPER_MODEL")) or "base",
        whisper_language=_clean_env_value(os.getenv("WHISPER_LANGUAGE")),
    )
