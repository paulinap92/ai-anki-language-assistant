"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.domain.languages import normalize_language


load_dotenv()


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
    audio_cache_dir: str


def get_settings() -> Settings:
    """Load settings from environment variables.

    Returns:
        Application settings.

    Raises:
        ValueError: If no AI provider API key is configured.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if not gemini_api_key and not openai_api_key and not anthropic_api_key:
        raise ValueError(
            "Configure at least one API key in .env: GEMINI_API_KEY, "
            "OPENAI_API_KEY, or ANTHROPIC_API_KEY."
        )

    return Settings(
        gemini_api_key=gemini_api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        anthropic_api_key=anthropic_api_key,
        claude_model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5"),
        anki_connect_url=os.getenv("ANKI_CONNECT_URL", "http://localhost:8765"),
        anki_deck_name=os.getenv("ANKI_DECK_NAME", "AI Vocabulary"),
        default_target_language=normalize_language(
            os.getenv("DEFAULT_TARGET_LANGUAGE", "English")
        ),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        elevenlabs_tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "coral"),
        gemini_tts_model=os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview"),
        gemini_tts_voice=os.getenv("GEMINI_TTS_VOICE", "Kore"),
        piper_model_path=os.getenv("PIPER_MODEL_PATH"),
        audio_cache_dir=os.getenv("AUDIO_CACHE_DIR", ".audio_cache"),
    )
