"""Modern CustomTkinter GUI entry point for the AI Anki Vocabulary Generator."""

import customtkinter as ctk

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.core.config import get_settings
from src.ui.modern_gui import ModernVocabularyGui


def main() -> None:
    """Run the modern desktop application."""
    settings = get_settings()
    ai_clients = build_ai_clients(settings)

    anki_client = AnkiClient(
        anki_connect_url=settings.anki_connect_url,
        deck_name=settings.anki_deck_name,
    )

    root = ctk.CTk()
    ModernVocabularyGui(
        root=root,
        ai_clients=ai_clients,
        anki_client=anki_client,
        default_target_language=settings.default_target_language,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
