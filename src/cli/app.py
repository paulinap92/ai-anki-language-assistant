"""Main command-line application loop for generating vocabulary cards."""

from src.ai.base import VocabularyAiClient
from src.anki.client import AnkiClient
from src.domain.languages import SUPPORTED_LANGUAGES, normalize_language


STOP_COMMANDS = {"stop", "exit", "quit", "q"}
DECK_COMMANDS = {"/deck", "deck", "change deck"}
LANGUAGE_COMMANDS = {"/language", "language", "lang", "/lang"}
MODEL_COMMANDS = {"/model", "model", "provider", "/provider"}


class VocabularyApp:
    """Command-line application for AI-generated Anki flashcards."""

    def __init__(
        self,
        ai_clients: dict[str, VocabularyAiClient],
        anki_client: AnkiClient,
        default_target_language: str,
    ) -> None:
        """Initialize the application."""
        self._ai_clients = ai_clients
        self._anki_client = anki_client
        self._target_language = default_target_language
        self._provider_name = next(iter(ai_clients))

    @property
    def _ai_client(self) -> VocabularyAiClient:
        """Return the currently selected AI provider client."""
        return self._ai_clients[self._provider_name]

    def run(self) -> None:
        """Run the interactive vocabulary flashcard generator."""
        print("=" * 60)
        print("AI ANKI VOCABULARY GENERATOR")
        print("=" * 60)
        print("Type a word or phrase in the selected target language.")
        print("Type '/model' to change AI provider.")
        print("Type '/language' to change language.")
        print("Type '/deck' to change the target Anki deck.")
        print("Type 'stop' to finish.")
        print()

        self._select_provider()
        self._select_language()
        self._select_deck()

        while True:
            print(f"Current model: {self._provider_name}")
            print(f"Current language: {self._target_language}")
            print(f"Current deck: {self._anki_client.deck_name}")
            word_or_phrase = input("Word or phrase: ").strip()

            if not word_or_phrase:
                print("Please enter a word or phrase.")
                continue

            normalized_input = word_or_phrase.lower()
            if normalized_input in STOP_COMMANDS:
                print("Finished.")
                break
            if normalized_input in DECK_COMMANDS:
                self._select_deck()
                continue
            if normalized_input in LANGUAGE_COMMANDS:
                self._select_language()
                continue
            if normalized_input in MODEL_COMMANDS:
                self._select_provider()
                continue

            try:
                print(f"Generating flashcard with {self._provider_name}...")
                card = self._ai_client.generate_card(
                    word_or_phrase=word_or_phrase,
                    target_language=self._target_language,
                    explanation_language="Polish",
                )
                print()
                print(f"Word: {card.word_or_phrase}")
                print(f"Language: {card.target_language}")
                print(f"Definition: {card.definition}")
                print(f"Example: {card.example}")
                print(f"Synonyms: {', '.join(card.synonyms)}")
                print()
                self._anki_client.add_card(card, provider_name=self._provider_name)
                print(f"Added to Anki deck: {self._anki_client.deck_name}")
                print("-" * 60)
            except Exception as exc:
                print(f"Error: {exc}")
                print("-" * 60)

    def _select_provider(self) -> None:
        """Let the user choose one configured AI provider."""
        providers = list(self._ai_clients)
        print("Available AI providers:")
        for index, provider in enumerate(providers, start=1):
            print(f"{index}. {provider}")
        print(f"Current/default: {self._provider_name}")
        print()

        while True:
            choice = input("AI provider: ").strip()
            if not choice:
                break
            if choice.isdigit() and 1 <= int(choice) <= len(providers):
                self._provider_name = providers[int(choice) - 1]
                break
            print("Choose a provider number from the list or press Enter.")

        print(f"Selected AI provider: {self._provider_name}")
        print("-" * 60)

    def _select_language(self) -> None:
        """Let the user select a supported target language."""
        while True:
            print("Available languages:")
            for number, language in SUPPORTED_LANGUAGES.items():
                print(f"{number}. {language}")
            print(f"Current/default: {self._target_language}")
            print()

            choice = input("Language: ").strip()
            if not choice:
                selected_language = self._target_language
            elif choice in SUPPORTED_LANGUAGES:
                selected_language = SUPPORTED_LANGUAGES[choice]
            else:
                try:
                    selected_language = normalize_language(choice)
                except ValueError as exc:
                    print(f"Error: {exc}")
                    print("-" * 60)
                    continue

            self._target_language = selected_language
            print(f"Selected language: {self._target_language}")
            print("-" * 60)
            return

    def _select_deck(self) -> None:
        """Let the user select an existing deck or create a new one."""
        decks = self._anki_client.list_decks()
        print("Available Anki decks:")
        for index, deck in enumerate(decks, start=1):
            print(f"{index}. {deck}")
        print(f"Default: {self._anki_client.deck_name}")
        print()
        choice = input("Deck: ").strip()

        if not choice:
            selected_deck = self._anki_client.deck_name
        elif choice.isdigit() and 1 <= int(choice) <= len(decks):
            selected_deck = decks[int(choice) - 1]
        else:
            selected_deck = choice

        self._anki_client.set_deck(selected_deck)
        print(f"Selected deck: {self._anki_client.deck_name}")
        print("-" * 60)
