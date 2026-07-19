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

    def add_card(self, card: VocabularyCard, provider_name: str, extra_tags: list[str] | None = None) -> None:
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
                *(extra_tags or []),
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

    def existing_vocabulary_note_map(self) -> dict[str, int]:
        """Return app vocabulary note IDs indexed by normalized word value.

        This is kept for backwards compatibility with older workflows. Newer
        duplicate prechecks should use :meth:`existing_note_map_broad` so old
        Basic/legacy cards are detected too.
        """
        broad = self.existing_note_map_broad(model_query=MODEL_NAME)
        return {word: int(summary["note_id"]) for word, summary in broad.items()}

    def existing_note_map_broad(
        self,
        model_query: str = "",
        *,
        include_all_decks: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Return existing notes indexed by normalized word/phrase.

        By default this scans all note types in the selected deck. For duplicate
        prechecks before provider API calls, pass ``include_all_decks=True`` so
        cards already present in another deck are detected before Gemini/OpenAI/
        Claude is called. This mirrors Anki's duplicate behaviour more closely
        and prevents API quota waste when the same word exists elsewhere.
        """
        query_parts: list[str] = []
        if not include_all_decks:
            deck = self._escape_search_value(self._deck_name)
            query_parts.append(f'deck:"{deck}"')
        if model_query.strip():
            query_parts.append(f'note:"{self._escape_search_value(model_query.strip())}"')
        note_ids = self._invoke(
            action="findNotes",
            params={"query": " ".join(query_parts)},
        ) or []
        if not note_ids:
            return {}

        notes = self._invoke(action="notesInfo", params={"notes": note_ids}) or []
        result: dict[str, dict[str, Any]] = {}
        for note in notes:
            summary = self._summarise_note(note)
            normalized = self._normalise_field_value(str(summary.get("word", "")))
            if not normalized:
                continue
            if normalized in result:
                result[normalized]["duplicate_count"] = int(result[normalized].get("duplicate_count", 1)) + 1
                continue
            summary["duplicate_count"] = 1
            result[normalized] = summary
        return result

    def add_card_without_duplicate_scan(
        self, card: VocabularyCard, provider_name: str, extra_tags: list[str] | None = None
    ) -> None:
        """Add one vocabulary card without an extra exact-match deck scan."""
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
                *(extra_tags or []),
            ],
        }
        result = self._invoke(action="addNote", params={"note": note})
        if result is None:
            raise ValueError(f"Could not add card: {card.word_or_phrase}")

    def update_card_by_note_id(
        self, note_id: int, card: VocabularyCard, provider_name: str, extra_tags: list[str] | None = None
    ) -> int:
        """Replace fields of an existing vocabulary note by known note ID."""
        self.ensure_vocabulary_model_exists()
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
                "tags": " ".join([f"provider_{provider_name.lower()}", *(extra_tags or [])]),
            },
        )
        return note_id

    def update_card(self, card: VocabularyCard, provider_name: str, extra_tags: list[str] | None = None) -> int:
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
                "tags": " ".join([f"provider_{provider_name.lower()}", *(extra_tags or [])]),
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

    AUDIO_FIELD_CANDIDATES = ("Audio", "WordAudio", "ExampleAudio", "SentenceAudio")
    WORD_FIELD_CANDIDATES = ("Word", "Front", "Expression", "Phrase", "Term")
    EXAMPLE_FIELD_CANDIDATES = ("Example", "Sentence", "ExampleSentence", "Back")

    def list_vocabulary_notes_for_audio(
        self, missing_only: bool = True, search_query: str = ""
    ) -> list[dict[str, Any]]:
        """Return existing deck notes for audio enrichment.

        Historically this method scanned only the app's custom vocabulary note
        type. That missed older/legacy cards, so audio backfill now delegates to
        the same broad note scanner used by maintenance workflows.
        """
        return self.list_existing_notes(
            search_query=search_query,
            missing_audio_only=missing_only,
        )

    def list_existing_notes(
        self,
        search_query: str = "",
        missing_audio_only: bool = False,
        words: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return note summaries from the active deck for existing-card workflows.

        The method intentionally does not depend only on this app's custom note
        type. Older user-created notes can still be scanned, tagged, and checked
        for missing audio when they expose recognisable word/example/audio fields.
        """
        deck = self._escape_search_value(self._deck_name)
        query_parts = [f'deck:"{deck}"']
        if search_query.strip():
            query_parts.append(search_query.strip())
        query = " ".join(query_parts)
        note_ids = self._invoke(action="findNotes", params={"query": query}) or []
        if not note_ids:
            return []
        notes = self._invoke(action="notesInfo", params={"notes": note_ids}) or []
        word_filter = {self._normalise_field_value(word) for word in words or [] if word.strip()}
        result: list[dict[str, Any]] = []
        for raw_note in notes:
            summary = self._summarise_note(raw_note)
            if not summary["word"]:
                continue
            if word_filter and self._normalise_field_value(str(summary["word"])) not in word_filter:
                continue
            if missing_audio_only and summary["audio_status"] == "has_audio":
                continue
            result.append(summary)
        return result

    def add_tags_to_notes(self, note_ids: list[int], tags: str | list[str]) -> None:
        """Add one or more tags to existing notes."""
        if not note_ids:
            return
        tag_text = " ".join(tags) if isinstance(tags, list) else tags
        self._invoke(action="addTags", params={"notes": note_ids, "tags": tag_text})

    def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        """Update selected fields of an existing note without creating a duplicate."""
        self._invoke(
            action="updateNoteFields",
            params={"note": {"id": note_id, "fields": fields}},
        )

    def attach_audio_to_note(
        self, note_id: int, media_filename: str, field_name: str = "Audio"
    ) -> None:
        """Set an Anki sound reference on an existing note audio field."""
        self._invoke(
            action="updateNoteFields",
            params={
                "note": {
                    "id": note_id,
                    "fields": {field_name or "Audio": f"[sound:{media_filename}]"},
                }
            },
        )

    def append_audio_to_note(
        self, note_id: int, media_filename: str, field_name: str
    ) -> None:
        """Append an Anki sound reference to an existing text field.

        This is the safe legacy-card mode for old Basic cards that do not have a
        dedicated Audio field yet. The note type is not changed.
        """
        if not field_name:
            raise ValueError("Choose a target field for appended audio.")
        notes = self._invoke(action="notesInfo", params={"notes": [note_id]}) or []
        if not notes:
            raise ValueError(f"Could not read note {note_id} before appending audio.")
        fields = notes[0].get("fields") or {}
        if field_name not in fields:
            raise ValueError(f"Field '{field_name}' does not exist on note {note_id}.")
        current_value = (fields.get(field_name) or {}).get("value", "")
        sound = f"[sound:{media_filename}]"
        if "[sound:" in str(current_value).casefold():
            updated_value = str(current_value)
        elif current_value:
            updated_value = f"{current_value}<br>{sound}"
        else:
            updated_value = sound
        self._invoke(
            action="updateNoteFields",
            params={"note": {"id": note_id, "fields": {field_name: updated_value}}},
        )

    def _summarise_note(self, note: dict[str, Any]) -> dict[str, Any]:
        """Normalize an AnkiConnect notesInfo object for UI workflows."""
        fields = note.get("fields") or {}
        field_values = {
            name: (payload or {}).get("value", "")
            for name, payload in fields.items()
        }
        word_field = self._first_existing_field(field_values, self.WORD_FIELD_CANDIDATES)
        example_field = self._first_existing_field(field_values, self.EXAMPLE_FIELD_CANDIDATES)
        audio_field = self._first_existing_field(field_values, self.AUDIO_FIELD_CANDIDATES)
        audio_value = field_values.get(audio_field, "") if audio_field else ""
        if not audio_field:
            legacy_sound_field = self._first_field_containing_sound(field_values)
            if legacy_sound_field:
                audio_field = legacy_sound_field
                audio_value = field_values.get(audio_field, "")
        audio_status = self._audio_status(audio_field, audio_value)
        return {
            "note_id": int(note["noteId"]),
            "model": note.get("modelName", ""),
            "tags": list(note.get("tags") or []),
            "fields": field_values,
            "word_field": word_field,
            "example_field": example_field,
            "audio_field": audio_field,
            "word": self._plain_field_value(field_values.get(word_field, "")) if word_field else "",
            "example": self._plain_field_value(field_values.get(example_field, "")) if example_field else "",
            "language": self._plain_field_value(field_values.get("Language", "")),
            "audio": audio_value,
            "audio_status": audio_status,
        }

    @classmethod
    def _first_existing_field(
        cls, field_values: dict[str, str], candidates: tuple[str, ...]
    ) -> str:
        for name in candidates:
            if name in field_values:
                return name
        return ""

    @staticmethod
    def _first_field_containing_sound(field_values: dict[str, str]) -> str:
        for name, value in field_values.items():
            if "[sound:" in str(value or "").casefold():
                return name
        return ""

    @staticmethod
    def _audio_status(audio_field: str, audio_value: str) -> str:
        if not audio_field:
            return "missing_audio_field"
        normalized = AnkiClient._normalise_field_value(audio_value)
        if not normalized:
            return "missing_audio"
        if "[sound:" in (audio_value or "").casefold():
            return "has_audio"
        return "malformed_audio"

    @staticmethod
    def _plain_field_value(value: str) -> str:
        plain = re.sub(r"<[^>]+>", " ", unescape(value or ""))
        return " ".join(plain.split())

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
