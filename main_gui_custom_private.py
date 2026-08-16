"""Discreet CustomTkinter GUI launcher for local/private testing."""

from pathlib import Path

import customtkinter as ctk

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.core.config import get_settings
from src.speech import LocalWhisperSttService, SpeechService
from src.speech.tts.factory import build_tts_providers
from src.ui.modern_gui import ModernVocabularyGui


def main() -> None:
    settings = get_settings()
    ai_clients = build_ai_clients(settings)
    anki_client = AnkiClient(
        anki_connect_url=settings.anki_connect_url,
        deck_name=settings.anki_deck_name,
    )

    tts_providers = build_tts_providers(settings)
    speech_service = SpeechService(tts_providers, Path(settings.audio_cache_dir)) if tts_providers else None
    stt_service = None
    if settings.stt_provider.lower() in {"local_whisper", "whisper", "faster_whisper"}:
        stt_service = LocalWhisperSttService(
            model_name=settings.whisper_model,
            language=settings.whisper_language,
            cache_dir=settings.audio_cache_dir,
        )

    root = ctk.CTk()
    ModernVocabularyGui(
        root=root,
        ai_clients=ai_clients,
        anki_client=anki_client,
        default_target_language=settings.default_target_language,
        speech_service=speech_service,
        stt_service=stt_service,
        window_title=" ",
        show_public_header=False,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
