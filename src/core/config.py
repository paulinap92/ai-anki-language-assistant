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


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse common truthy/falsy environment values."""
    value = _clean_env_value(os.getenv(name))
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    setup_mode: str
    gemini_api_key: str | None
    gemini_model: str
    gemini_import_model: str
    gemini_multimodal_model: str
    gemini_review_model: str
    openai_api_key: str | None
    openai_model: str
    openai_import_model: str
    openai_multimodal_model: str
    openai_review_model: str
    openai_premium_model: str | None
    openrouter_api_key: str | None
    openrouter_model: str
    openrouter_import_model: str
    openrouter_review_model: str
    anthropic_api_key: str | None
    claude_model: str
    claude_import_model: str
    claude_review_model: str
    claude_premium_model: str | None
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
    piper_voice_de: str | None
    piper_voice_fr: str | None
    piper_voice_it: str | None
    piper_voice_pt: str | None
    ollama_base_url: str
    ollama_model: str | None
    audio_cache_dir: str
    stt_provider: str
    openai_stt_model: str
    groq_api_key: str | None
    groq_stt_model: str
    whisper_model: str
    whisper_language: str | None
    langsmith_tracing: bool
    langsmith_api_key: str | None
    langsmith_project: str
    langsmith_endpoint: str | None
    langsmith_redact_inputs: bool


def get_settings() -> Settings:
    """Load settings from environment variables.

    Returns:
        Application settings.

    The GUI is allowed to start with no provider configured so first-time users
    can open the Setup tab and choose Local, Hybrid/BYOK or API/BYOK.
    """
    gemini_api_key = _clean_env_value(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    openai_api_key = _clean_env_value(os.getenv("OPENAI_API_KEY"))
    openrouter_api_key = _clean_env_value(os.getenv("OPENROUTER_API_KEY"))
    groq_api_key = _clean_env_value(os.getenv("GROQ_API_KEY"))
    anthropic_api_key = _clean_env_value(os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"))

    langsmith_api_key = _clean_env_value(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
    langsmith_project = (
        _clean_env_value(os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT"))
        or "ai-anki-language-assistant"
    )
    langsmith_endpoint = _clean_env_value(os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT"))
    langsmith_tracing = _env_bool("LANGSMITH_TRACING", _env_bool("LANGCHAIN_TRACING_V2", False))
    langsmith_redact_inputs = _env_bool("LANGSMITH_REDACT_INPUTS", True)

    ollama_model = _clean_env_value(os.getenv("OLLAMA_MODEL"))

    requested_mode = (_clean_env_value(os.getenv("AI_SETUP_MODE")) or "").casefold()
    aliases = {
        "local": "local",
        "fully local": "local",
        "offline": "local",
        "hybrid": "hybrid",
        "byok": "hybrid",
        "local + api": "hybrid",
        "api": "api",
        "cloud": "api",
        "cloud / api": "api",
    }
    if requested_mode in aliases:
        setup_mode = aliases[requested_mode]
    else:
        has_cloud = bool(gemini_api_key or openai_api_key or openrouter_api_key or groq_api_key or anthropic_api_key)
        if ollama_model and has_cloud:
            setup_mode = "hybrid"
        elif ollama_model:
            setup_mode = "local"
        elif has_cloud:
            setup_mode = "api"
        else:
            # First run: keep the GUI available so the user can configure a
            # local, hybrid or BYOK setup instead of crashing before startup.
            setup_mode = "hybrid"

    return Settings(
        setup_mode=setup_mode,
        gemini_api_key=gemini_api_key,
        gemini_model=_clean_env_value(os.getenv("GEMINI_MODEL")) or "gemini-2.5-flash",
        gemini_import_model=(
            _clean_env_value(os.getenv("GEMINI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("GEMINI_MODEL"))
            or "gemini-2.5-flash"
        ),
        gemini_multimodal_model=(
            _clean_env_value(os.getenv("GEMINI_MULTIMODAL_MODEL"))
            or _clean_env_value(os.getenv("GEMINI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("GEMINI_MODEL"))
            or "gemini-2.5-flash"
        ),
        gemini_review_model=(
            _clean_env_value(os.getenv("GEMINI_REVIEW_MODEL"))
            or _clean_env_value(os.getenv("GEMINI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("GEMINI_MODEL"))
            or "gemini-2.5-flash"
        ),
        openai_api_key=openai_api_key,
        openai_model=_clean_env_value(os.getenv("OPENAI_MODEL")) or "gpt-4.1-mini",
        openai_import_model=(
            _clean_env_value(os.getenv("OPENAI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("OPENAI_MODEL"))
            or "gpt-4.1-mini"
        ),
        openai_multimodal_model=(
            _clean_env_value(os.getenv("OPENAI_MULTIMODAL_MODEL"))
            or _clean_env_value(os.getenv("OPENAI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("OPENAI_MODEL"))
            or "gpt-4.1-mini"
        ),
        openai_review_model=(
            _clean_env_value(os.getenv("OPENAI_REVIEW_MODEL"))
            or _clean_env_value(os.getenv("OPENAI_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("OPENAI_MODEL"))
            or "gpt-4.1-mini"
        ),
        openai_premium_model=_clean_env_value(os.getenv("OPENAI_PREMIUM_MODEL")),
        openrouter_api_key=openrouter_api_key,
        openrouter_model=_clean_env_value(os.getenv("OPENROUTER_MODEL")) or "openrouter/free",
        openrouter_import_model=(
            _clean_env_value(os.getenv("OPENROUTER_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("OPENROUTER_MODEL"))
            or "openrouter/free"
        ),
        openrouter_review_model=(
            _clean_env_value(os.getenv("OPENROUTER_REVIEW_MODEL"))
            or _clean_env_value(os.getenv("OPENROUTER_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("OPENROUTER_MODEL"))
            or "openrouter/free"
        ),
        anthropic_api_key=anthropic_api_key,
        claude_model=_clean_env_value(os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL")) or "claude-haiku-4-5",
        claude_import_model=(
            _clean_env_value(os.getenv("CLAUDE_IMPORT_MODEL") or os.getenv("ANTHROPIC_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL"))
            or "claude-haiku-4-5"
        ),
        claude_review_model=(
            _clean_env_value(os.getenv("CLAUDE_REVIEW_MODEL") or os.getenv("ANTHROPIC_REVIEW_MODEL"))
            or _clean_env_value(os.getenv("CLAUDE_IMPORT_MODEL") or os.getenv("ANTHROPIC_IMPORT_MODEL"))
            or _clean_env_value(os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL"))
            or "claude-haiku-4-5"
        ),
        claude_premium_model=_clean_env_value(os.getenv("CLAUDE_PREMIUM_MODEL") or os.getenv("ANTHROPIC_PREMIUM_MODEL")),
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
        piper_voice_de=_clean_env_value(os.getenv("PIPER_VOICE_DE")),
        piper_voice_fr=_clean_env_value(os.getenv("PIPER_VOICE_FR")),
        piper_voice_it=_clean_env_value(os.getenv("PIPER_VOICE_IT")),
        piper_voice_pt=_clean_env_value(os.getenv("PIPER_VOICE_PT")),
        ollama_base_url=_clean_env_value(os.getenv("OLLAMA_BASE_URL")) or "http://localhost:11434",
        ollama_model=ollama_model,
        audio_cache_dir=_clean_env_value(os.getenv("AUDIO_CACHE_DIR")) or ".audio_cache",
        stt_provider=_clean_env_value(os.getenv("STT_PROVIDER")) or "local_whisper",
        openai_stt_model=_clean_env_value(os.getenv("OPENAI_STT_MODEL")) or "gpt-4o-mini-transcribe",
        groq_api_key=groq_api_key,
        groq_stt_model=_clean_env_value(os.getenv("GROQ_STT_MODEL")) or "whisper-large-v3-turbo",
        whisper_model=_clean_env_value(os.getenv("WHISPER_MODEL")) or "small",
        whisper_language=_clean_env_value(os.getenv("WHISPER_LANGUAGE")),
        langsmith_tracing=langsmith_tracing,
        langsmith_api_key=langsmith_api_key,
        langsmith_project=langsmith_project,
        langsmith_endpoint=langsmith_endpoint,
        langsmith_redact_inputs=langsmith_redact_inputs,
    )
