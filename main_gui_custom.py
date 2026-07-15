"""Modern CustomTkinter GUI entry point for the AI Anki Vocabulary Generator."""

import customtkinter as ctk

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.core.config import get_settings
from src.ui.modern_gui import ModernVocabularyGui
from src.speech import SpeechService
from src.speech.tts.factory import build_tts_providers
from pathlib import Path


def main() -> None:
    """Run the modern desktop application."""
    settings = get_settings()
    ai_clients = build_ai_clients(settings)

    anki_client = AnkiClient(
        anki_connect_url=settings.anki_connect_url,
        deck_name=settings.anki_deck_name,
    )

    tts_providers = build_tts_providers(settings)
    speech_service = SpeechService(tts_providers, Path(settings.audio_cache_dir))

    root = ctk.CTk()
    ModernVocabularyGui(
        root=root,
        ai_clients=ai_clients,
        anki_client=anki_client,
        default_target_language=settings.default_target_language,
        speech_service=speech_service,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
