"""AnkiConnect client for decks, note models, and vocabulary cards."""

from __future__ import annotations

from typing import Any

import requests

from src.anki.field_builder import GrammarFieldBuilder, VocabularyFieldBuilder
from src.anki.templates import (
    BACK_TEMPLATE,
    CARD_CSS,
    FRONT_TEMPLATE,
    GRAMMAR_BACK_TEMPLATE,
    GRAMMAR_CARD_CSS,
    GRAMMAR_FRONT_TEMPLATE,
    GRAMMAR_MODEL_FIELDS,
    GRAMMAR_MODEL_NAME,
    LEGACY_BACK_TEMPLATE,
    LEGACY_FRONT_TEMPLATE,
    LEGACY_MODEL_FIELDS,
    LEGACY_MODEL_NAME,
    MODEL_FIELDS,
    MODEL_NAME,
)
from src.domain.languages import get_language_tag
from src.domain.models import GrammarAnalysis, VocabularyCard


class AnkiClient:
    """Small wrapper around the local AnkiConnect HTTP API.

    Responsibilities:
    - list and create decks;
    - create or update the custom vocabulary note type;
    - create or update the migration note type for old Basic cards;
    - add validated vocabulary cards to the selected deck.

    The class deliberately does not know how AI content is generated. It receives
    already validated ``VocabularyCard`` objects and sends them to Anki.
    """

    def __init__(self, anki_connect_url: str, deck_name: str) -> None:
        """Initialize the client.

        Args:
            anki_connect_url: Local AnkiConnect endpoint, usually
                ``http://localhost:8765``.
            deck_name: Default deck used when adding notes.
        """
        self._url = anki_connect_url
        self._deck_name = deck_name
        self._model_ready = False
        self._grammar_model_ready = False

    @property
    def deck_name(self) -> str:
        """Return the currently selected Anki deck name."""
        return self._deck_name

    def set_deck(self, deck_name: str) -> None:
        """Set the active deck and create it in Anki if it does not exist."""
        self._deck_name = deck_name.strip()
        self.ensure_deck_exists()

    def list_decks(self) -> list[str]:
        """Return all deck names available in the currently open Anki profile."""
        result = self._invoke(action="deckNames")
        return sorted(result or [])

    def ensure_deck_exists(self) -> None:
        """Create the currently selected deck if it does not already exist."""
        self._invoke(action="createDeck", params={"deck": self._deck_name})

    def ensure_vocabulary_model_exists(self) -> None:
        """Create or update the main custom vocabulary note type.

        The method is idempotent. It creates the note type on first run and later
        updates the CSS/templates, which lets card design changes propagate to
        existing Anki installations without manual work.
        """
        if self._model_ready:
            return

        model_names = self._invoke(action="modelNames") or []
        if MODEL_NAME not in model_names:
            self._create_model(
                model_name=MODEL_NAME,
                fields=MODEL_FIELDS,
                front_template=FRONT_TEMPLATE,
                back_template=BACK_TEMPLATE,
            )
        else:
            self._update_model(
                model_name=MODEL_NAME,
                front_template=FRONT_TEMPLATE,
                back_template=BACK_TEMPLATE,
            )

        self._model_ready = True

    def ensure_grammar_model_exists(self) -> None:
        """Create or update the custom grammar note type."""
        if self._grammar_model_ready:
            return

        model_names = self._invoke(action="modelNames") or []
        if GRAMMAR_MODEL_NAME not in model_names:
            self._create_model(
                model_name=GRAMMAR_MODEL_NAME,
                fields=GRAMMAR_MODEL_FIELDS,
                front_template=GRAMMAR_FRONT_TEMPLATE,
                back_template=GRAMMAR_BACK_TEMPLATE,
                template_name="Grammar Card",
                css=GRAMMAR_CARD_CSS,
            )
        else:
            self._update_model(
                model_name=GRAMMAR_MODEL_NAME,
                front_template=GRAMMAR_FRONT_TEMPLATE,
                back_template=GRAMMAR_BACK_TEMPLATE,
                template_name="Grammar Card",
                css=GRAMMAR_CARD_CSS,
            )

        self._grammar_model_ready = True

    def prepare_legacy_card_migration(self) -> int:
        """Prepare a migration note type and open old app cards in Anki Browse.

        Returns:
            Number of old app-created Basic cards shown by the Anki Browser query.
        """
        model_names = self._invoke(action="modelNames") or []
        if LEGACY_MODEL_NAME not in model_names:
            self._create_model(
                model_name=LEGACY_MODEL_NAME,
                fields=LEGACY_MODEL_FIELDS,
                front_template=LEGACY_FRONT_TEMPLATE,
                back_template=LEGACY_BACK_TEMPLATE,
            )
        else:
            self._update_model(
                model_name=LEGACY_MODEL_NAME,
                front_template=LEGACY_FRONT_TEMPLATE,
                back_template=LEGACY_BACK_TEMPLATE,
            )

        old_cards = self._invoke(
            action="guiBrowse",
            params={"query": "tag:ai_vocabulary -tag:ai_vocabulary_light_card note:Basic"},
        ) or []
        return len(old_cards)

    def add_card(self, card: VocabularyCard, provider_name: str) -> None:
        """Add one vocabulary card to the active Anki deck.

        Args:
            card: Validated vocabulary content.
            provider_name: AI provider name used for the Anki tag.

        Raises:
            ValueError: If Anki rejects the note, usually because it is a duplicate.
        """
        self.ensure_vocabulary_model_exists()
        language_tag = get_language_tag(card.target_language)
        note = {
            "deckName": self._deck_name,
            "modelName": MODEL_NAME,
            "fields": VocabularyFieldBuilder.build_fields(card),
            "options": {"allowDuplicate": False},
            "tags": [
                "ai_vocabulary",
                "ai_vocabulary_light_card",
                language_tag,
                f"provider_{provider_name.lower()}",
            ],
        }

        result = self._invoke(action="addNote", params={"note": note})
        if result is None:
            raise ValueError(
                f"Card already exists or could not be added: {card.word_or_phrase}"
            )

    def add_grammar_card(self, card: GrammarAnalysis, provider_name: str) -> None:
        """Add one sentence-first grammar card to the active Anki deck."""
        self.ensure_grammar_model_exists()
        language_tag = get_language_tag(card.target_language)
        note = {
            "deckName": self._deck_name,
            "modelName": GRAMMAR_MODEL_NAME,
            "fields": GrammarFieldBuilder.build_fields(card),
            "options": {"allowDuplicate": False},
            "tags": [
                "ai_grammar",
                "ai_grammar_light_card",
                language_tag,
                f"provider_{provider_name.lower()}",
            ],
        }

        result = self._invoke(action="addNote", params={"note": note})
        if result is None:
            raise ValueError(
                f"Grammar card already exists or could not be added: {card.sentence}"
            )

    def _create_model(
        self,
        model_name: str,
        fields: list[str],
        front_template: str,
        back_template: str,
        template_name: str = "Vocabulary Card",
        css: str = CARD_CSS,
    ) -> None:
        """Create an Anki note type with one card template."""
        self._invoke(
            action="createModel",
            params={
                "modelName": model_name,
                "inOrderFields": fields,
                "css": css,
                "isCloze": False,
                "cardTemplates": [
                    {
                        "Name": template_name,
                        "Front": front_template,
                        "Back": back_template,
                    }
                ],
            },
        )

    def _update_model(
        self,
        model_name: str,
        front_template: str,
        back_template: str,
        template_name: str = "Vocabulary Card",
        css: str = CARD_CSS,
    ) -> None:
        """Update styling and templates for an existing Anki note type."""
        self._invoke(
            action="updateModelStyling",
            params={"model": {"name": model_name, "css": css}},
        )
        self._invoke(
            action="updateModelTemplates",
            params={
                "model": {
                    "name": model_name,
                    "templates": {
                        template_name: {
                            "Front": front_template,
                            "Back": back_template,
                        }
                    },
                }
            },
        )

    def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """Call AnkiConnect and return the ``result`` field.

        Raises:
            ConnectionError: If Anki or AnkiConnect is not reachable.
            RuntimeError: If AnkiConnect returns an application-level error.
            requests.HTTPError: If the HTTP request fails.
        """
        payload = {"action": action, "version": 6, "params": params or {}}
        try:
            response = requests.post(self._url, json=payload, timeout=10)
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(
                "Could not connect to Anki. Make sure Anki is open "
                "and AnkiConnect is installed."
            ) from exc

        response.raise_for_status()
        data = response.json()
        if data.get("error") is not None:
            raise RuntimeError(f"AnkiConnect error: {data['error']}")
        return data.get("result")
