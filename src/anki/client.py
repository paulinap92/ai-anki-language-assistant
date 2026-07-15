"""AnkiConnect client for decks, note models, and vocabulary cards."""

from __future__ import annotations

from html import unescape
import base64
from pathlib import Path
import re
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


class DuplicateNoteError(ValueError):
    """Raised when a matching Anki note already exists."""

    def __init__(self, message: str, note_id: int) -> None:
        super().__init__(message)
        self.note_id = note_id


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


    def find_cards_for_practice(self, query: str) -> list[dict[str, Any]]:
        """Return detailed Anki card records matching a browser search query."""
        card_ids = self._invoke(action="findCards", params={"query": query}) or []
        if not card_ids:
            return []
        return self._invoke(action="cardsInfo", params={"cards": card_ids}) or []

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
            self._ensure_model_fields(MODEL_NAME, MODEL_FIELDS)
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

        existing_note_id = self.find_existing_vocabulary_note_id(card.word_or_phrase)
        if existing_note_id is not None:
            raise DuplicateNoteError(
                f"A vocabulary card for '{card.word_or_phrase}' already exists.",
                existing_note_id,
            )

        result = self._invoke(action="addNote", params={"note": note})
        if result is None:
            raise ValueError(f"Could not add card: {card.word_or_phrase}")

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

        existing_note_id = self.find_existing_grammar_note_id(card.sentence)
        if existing_note_id is not None:
            raise DuplicateNoteError(
                f"A grammar card for this sentence already exists: {card.sentence}",
                existing_note_id,
            )

        result = self._invoke(action="addNote", params={"note": note})
        if result is None:
            raise ValueError(f"Could not add grammar card: {card.sentence}")

    def find_existing_vocabulary_note_id(self, word_or_phrase: str) -> int | None:
        """Return the exact matching vocabulary note ID in the active deck."""
        return self._find_existing_note_id(
            model_name=MODEL_NAME,
            field_name="Word",
            expected_value=word_or_phrase,
        )

    def find_existing_grammar_note_id(self, sentence: str) -> int | None:
        """Return the exact matching grammar note ID in the active deck."""
        return self._find_existing_note_id(
            model_name=GRAMMAR_MODEL_NAME,
            field_name="Sentence",
            expected_value=sentence,
        )

    def update_card(self, card: VocabularyCard, provider_name: str) -> int:
        """Replace fields of an existing vocabulary note and return its ID."""
        self.ensure_vocabulary_model_exists()
        note_id = self.find_existing_vocabulary_note_id(card.word_or_phrase)
        if note_id is None:
            raise ValueError(f"No existing card found for: {card.word_or_phrase}")
        fields = VocabularyFieldBuilder.build_fields(card)
        if not fields.get("Audio"):
            existing = self._invoke(action="notesInfo", params={"notes": [note_id]}) or []
            if existing:
                fields["Audio"] = (existing[0].get("fields", {}).get("Audio", {}) or {}).get("value", "")
        self._invoke(
            action="updateNoteFields",
            params={"note": {"id": note_id, "fields": fields}},
        )
        self._invoke(
            action="addTags",
            params={
                "notes": [note_id],
                "tags": f"provider_{provider_name.lower()}",
            },
        )
        return note_id

    def update_grammar_card(self, card: GrammarAnalysis, provider_name: str) -> int:
        """Replace fields of an existing grammar note and return its ID."""
        self.ensure_grammar_model_exists()
        note_id = self.find_existing_grammar_note_id(card.sentence)
        if note_id is None:
            raise ValueError(f"No existing grammar card found for: {card.sentence}")
        self._invoke(
            action="updateNoteFields",
            params={
                "note": {
                    "id": note_id,
                    "fields": GrammarFieldBuilder.build_fields(card),
                }
            },
        )
        self._invoke(
            action="addTags",
            params={
                "notes": [note_id],
                "tags": f"provider_{provider_name.lower()}",
            },
        )
        return note_id

    def store_media_file(self, file_path: Path) -> str:
        """Copy a local audio file into Anki media and return its media filename."""
        data = base64.b64encode(file_path.read_bytes()).decode("ascii")
        result = self._invoke(
            action="storeMediaFile",
            params={"filename": file_path.name, "data": data},
        )
        if not result:
            raise ValueError(f"Could not store Anki media file: {file_path.name}")
        return str(result)

    def list_vocabulary_notes_for_audio(self, missing_only: bool = True) -> list[dict[str, Any]]:
        """Return vocabulary notes from the active deck for audio enrichment."""
        self.ensure_vocabulary_model_exists()
        deck = self._escape_search_value(self._deck_name)
        model = self._escape_search_value(MODEL_NAME)
        note_ids = self._invoke(
            action="findNotes",
            params={"query": f'deck:"{deck}" note:"{model}"'},
        ) or []
        if not note_ids:
            return []
        notes = self._invoke(action="notesInfo", params={"notes": note_ids}) or []
        result: list[dict[str, Any]] = []
        for note in notes:
            fields = note.get("fields") or {}
            audio = (fields.get("Audio") or {}).get("value", "")
            if missing_only and self._normalise_field_value(audio):
                continue
            result.append({
                "note_id": int(note["noteId"]),
                "word": (fields.get("Word") or {}).get("value", ""),
                "example": (fields.get("Example") or {}).get("value", ""),
                "language": (fields.get("Language") or {}).get("value", ""),
                "audio": audio,
            })
        return result

    def attach_audio_to_note(self, note_id: int, media_filename: str) -> None:
        """Set an Anki sound reference on an existing vocabulary note."""
        self._invoke(
            action="updateNoteFields",
            params={
                "note": {
                    "id": note_id,
                    "fields": {"Audio": f"[sound:{media_filename}]"},
                }
            },
        )

    def _ensure_model_fields(self, model_name: str, fields: list[str]) -> None:
        """Add fields introduced after the note type was first created."""
        existing = self._invoke(
            action="modelFieldNames", params={"modelName": model_name}
        ) or []
        for field in fields:
            if field not in existing:
                self._invoke(
                    action="modelFieldAdd",
                    params={"modelName": model_name, "fieldName": field},
                )

    def _find_existing_note_id(
        self, model_name: str, field_name: str, expected_value: str
    ) -> int | None:
        """Find an exact field match without relying on Anki duplicate heuristics."""
        deck = self._escape_search_value(self._deck_name)
        model = self._escape_search_value(model_name)
        note_ids = self._invoke(
            action="findNotes",
            params={"query": f'deck:"{deck}" note:"{model}"'},
        ) or []
        if not note_ids:
            return None
        notes = self._invoke(action="notesInfo", params={"notes": note_ids}) or []
        expected = self._normalise_field_value(expected_value)
        for note in notes:
            field = (note.get("fields") or {}).get(field_name) or {}
            value = field.get("value", "")
            if self._normalise_field_value(value) == expected:
                return int(note["noteId"])
        return None

    @staticmethod
    def _escape_search_value(value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')

    @staticmethod
    def _normalise_field_value(value: str) -> str:
        plain = re.sub(r"<[^>]+>", "", unescape(value or ""))
        return " ".join(plain.split()).casefold()

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
