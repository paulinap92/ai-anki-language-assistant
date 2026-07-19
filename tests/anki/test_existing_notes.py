from src.anki.client import AnkiClient


def test_summarise_note_detects_missing_audio() -> None:
    client = AnkiClient("http://localhost:8765", "Deck")
    note = {
        "noteId": 123,
        "modelName": "AI Vocabulary Light Card",
        "tags": ["ai_vocabulary"],
        "fields": {
            "Word": {"value": "generous"},
            "Example": {"value": "She is generous with her time."},
            "Language": {"value": "English"},
            "Audio": {"value": ""},
        },
    }

    summary = client._summarise_note(note)

    assert summary["note_id"] == 123
    assert summary["word"] == "generous"
    assert summary["audio_field"] == "Audio"
    assert summary["audio_status"] == "missing_audio"


def test_summarise_note_detects_legacy_note_without_audio_field() -> None:
    client = AnkiClient("http://localhost:8765", "Deck")
    note = {
        "noteId": 456,
        "modelName": "Basic",
        "tags": [],
        "fields": {
            "Front": {"value": "stubborn"},
            "Back": {"value": "A stubborn person refuses to change their mind."},
        },
    }

    summary = client._summarise_note(note)

    assert summary["word"] == "stubborn"
    assert summary["audio_field"] == ""
    assert summary["audio_status"] == "missing_audio_field"


def test_audio_backfill_uses_broad_existing_note_scanner() -> None:
    class FakeAnkiClient(AnkiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8765", "Deck")
            self.calls = []

        def list_existing_notes(self, search_query: str = "", missing_audio_only: bool = False, words=None):  # type: ignore[override]
            self.calls.append(
                {
                    "search_query": search_query,
                    "missing_audio_only": missing_audio_only,
                    "words": words,
                }
            )
            return [{"note_id": 1, "word": "legacy", "audio_status": "missing_audio"}]

    client = FakeAnkiClient()

    result = client.list_vocabulary_notes_for_audio(missing_only=True, search_query="note:Basic")

    assert result[0]["word"] == "legacy"
    assert client.calls == [
        {"search_query": "note:Basic", "missing_audio_only": True, "words": None}
    ]


def test_summarise_note_detects_sound_in_legacy_back_field() -> None:
    client = AnkiClient("http://localhost:8765", "Deck")
    note = {
        "noteId": 789,
        "modelName": "Basic",
        "tags": [],
        "fields": {
            "Front": {"value": "outlast"},
            "Back": {"value": "przetrwać<br>[sound:outlast.mp3]"},
        },
    }

    summary = client._summarise_note(note)

    assert summary["audio_field"] == "Back"
    assert summary["audio_status"] == "has_audio"


def test_existing_note_map_broad_scans_all_note_types() -> None:
    class FakeAnkiClient(AnkiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8765", "Deck")
            self.queries = []

        def _invoke(self, action, params=None):  # type: ignore[override]
            if action == "findNotes":
                self.queries.append(params["query"])
                return [1, 2]
            if action == "notesInfo":
                return [
                    {
                        "noteId": 1,
                        "modelName": "Basic",
                        "tags": [],
                        "fields": {"Front": {"value": "outlast"}, "Back": {"value": "przetrwać"}},
                    },
                    {
                        "noteId": 2,
                        "modelName": "AI Vocabulary Light Card",
                        "tags": [],
                        "fields": {"Word": {"value": "appeal"}, "Audio": {"value": ""}},
                    },
                ]
            return None

    client = FakeAnkiClient()

    result = client.existing_note_map_broad()

    assert set(result) == {"outlast", "appeal"}
    assert result["outlast"]["model"] == "Basic"
    assert client.queries == ['deck:"Deck"']


def test_append_audio_to_note_appends_sound_to_existing_field() -> None:
    class FakeAnkiClient(AnkiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8765", "Deck")
            self.updated_fields = None

        def _invoke(self, action, params=None):  # type: ignore[override]
            if action == "notesInfo":
                return [{"fields": {"Back": {"value": "translation"}}}]
            if action == "updateNoteFields":
                self.updated_fields = params["note"]["fields"]
                return None
            return None

    client = FakeAnkiClient()

    client.append_audio_to_note(123, "outlast.mp3", "Back")

    assert client.updated_fields == {"Back": "translation<br>[sound:outlast.mp3]"}


def test_existing_note_map_broad_can_scan_all_decks() -> None:
    class FakeAnkiClient(AnkiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8765", "Deck")
            self.queries = []

        def _invoke(self, action, params=None):  # type: ignore[override]
            if action == "findNotes":
                self.queries.append(params["query"])
                return [1]
            if action == "notesInfo":
                return [
                    {
                        "noteId": 1,
                        "modelName": "AI Vocabulary Light Card",
                        "tags": [],
                        "fields": {"Word": {"value": "outlast"}, "Audio": {"value": ""}},
                    }
                ]
            return None

    client = FakeAnkiClient()

    result = client.existing_note_map_broad(include_all_decks=True)

    assert set(result) == {"outlast"}
    assert client.queries == [""]
