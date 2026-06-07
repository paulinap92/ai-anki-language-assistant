"""Command-line entry point for the AI Anki Vocabulary Generator."""

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.cli.app import VocabularyApp
from src.core.config import get_settings


def main() -> None:
    """Run the command-line application."""
    settings = get_settings()
    ai_clients = build_ai_clients(settings)

    anki_client = AnkiClient(
        anki_connect_url=settings.anki_connect_url,
        deck_name=settings.anki_deck_name,
    )

    app = VocabularyApp(
        ai_clients=ai_clients,
        anki_client=anki_client,
        default_target_language=settings.default_target_language,
    )
    app.run()


if __name__ == "__main__":
    main()
