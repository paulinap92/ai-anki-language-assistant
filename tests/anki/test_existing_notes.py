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
