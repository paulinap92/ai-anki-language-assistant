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


def test_summarise_grammar_note_is_ready_for_audio() -> None:
    client = AnkiClient("http://localhost:8765", "Deck")
    note = {
        "noteId": 321,
        "modelName": "AI Grammar Light Card",
        "tags": ["ai_grammar"],
        "fields": {
            "Sentence": {"value": "aunque + subjuntivo"},
            "Language": {"value": "Spanish"},
            "ContextExample": {"value": "Aunque sea difícil, voy a intentarlo."},
            "Audio": {"value": ""},
        },
    }

    summary = client._summarise_note(note)

    assert summary["word"] == "aunque + subjuntivo"
    assert summary["example"] == "Aunque sea difícil, voy a intentarlo."
    assert summary["audio_field"] == "Audio"
    assert summary["audio_status"] == "missing_audio"


def test_grammar_field_builder_includes_audio_fields() -> None:
    from src.anki.field_builder import GrammarFieldBuilder
    from src.domain.models import GrammarAnalysis

    card = GrammarAnalysis(
        sentence="aunque + subjuntivo",
        target_language="Spanish",
        meaning="Concesión hipotética.",
        structure="aunque + subjuntivo",
        breakdown=["aunque introduce concesión"],
        usage="Para situaciones hipotéticas.",
        context_example="Aunque sea difícil, voy a intentarlo.",
        contrasts=[],
        common_mistakes=[],
        audio="[sound:test.mp3]",
    )

    fields = GrammarFieldBuilder.build_fields(card)

    assert fields["Audio"] == "[sound:test.mp3]"
    assert fields["ExampleAudio"] == "[sound:test.mp3]"


def test_vocabulary_field_builder_includes_hidden_audio_metadata() -> None:
    from src.anki.field_builder import VocabularyFieldBuilder
    from src.domain.models import VocabularyCard

    card = VocabularyCard(
        word_or_phrase="short fuse",
        target_language="English",
        part_of_speech="idiom",
        definition="To become angry quickly.",
        translation="łatwo się denerwować",
        example="He has a short fuse when he is tired.",
        example_translation="Łatwo się denerwuje, kiedy jest zmęczony.",
        synonyms=[],
        collocations=[],
        grammar_note="",
        audio="[sound:short_fuse.mp3]",
    )

    fields = VocabularyFieldBuilder.build_fields(
        card,
        {
            "AudioProvider": "OpenAI",
            "AudioModel": "gpt-4o-mini-tts",
            "AudioVoice": "coral",
            "AudioVoiceLabel": "Coral",
            "AudioSourceText": "He has a short fuse when he is tired.",
            "AudioGeneratedAt": "2026-08-03T10:48:00",
            "AudioCacheKey": "anki_tts_abc",
            "AudioCached": "false",
            "AudioFile": "short_fuse.mp3",
        },
    )

    assert fields["Audio"] == "[sound:short_fuse.mp3]"
    assert fields["AudioProvider"] == "OpenAI"
    assert fields["AudioModel"] == "gpt-4o-mini-tts"
    assert fields["AudioVoice"] == "coral"
    assert fields["AudioVoiceLabel"] == "Coral"
    assert fields["AudioSourceText"] == "He has a short fuse when he is tired."
    assert fields["AudioCacheKey"] == "anki_tts_abc"
    assert fields["AudioCached"] == "false"
    assert fields["AudioFile"] == "short_fuse.mp3"


def test_attach_audio_to_note_writes_metadata_only_when_fields_exist() -> None:
    class FakeAnkiClient(AnkiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8765", "Deck")
            self.updated_fields = None

        def _invoke(self, action, params=None):  # type: ignore[override]
            if action == "notesInfo":
                return [
                    {
                        "fields": {
                            "Audio": {"value": ""},
                            "AudioProvider": {"value": ""},
                            "AudioModel": {"value": ""},
                            "AudioVoice": {"value": ""},
                        }
                    }
                ]
            if action == "updateNoteFields":
                self.updated_fields = params["note"]["fields"]
                return None
            return None

    client = FakeAnkiClient()

    client.attach_audio_to_note(
        123,
        "short_fuse.mp3",
        "Audio",
        audio_metadata={
            "AudioProvider": "OpenAI",
            "AudioModel": "gpt-4o-mini-tts",
            "AudioVoice": "coral",
            "AudioVoiceLabel": "Coral",
        },
    )

    assert client.updated_fields == {
        "Audio": "[sound:short_fuse.mp3]",
        "AudioProvider": "OpenAI",
        "AudioModel": "gpt-4o-mini-tts",
        "AudioVoice": "coral",
    }


def test_summarise_note_exposes_audio_metadata_for_preview() -> None:
    client = AnkiClient("http://localhost:8765", "Deck")
    note = {
        "noteId": 987,
        "modelName": "AI Vocabulary Light Card",
        "tags": [],
        "fields": {
            "Word": {"value": "short fuse"},
            "Example": {"value": "He has a short fuse when he is tired."},
            "Audio": {"value": "[sound:short_fuse.mp3]"},
            "AudioProvider": {"value": "OpenAI"},
            "AudioModel": {"value": "gpt-4o-mini-tts"},
            "AudioVoice": {"value": "coral"},
            "AudioVoiceLabel": {"value": "Coral"},
            "AudioGeneratedAt": {"value": "2026-08-03T10:48:00"},
        },
    }

    summary = client._summarise_note(note)

    assert summary["audio_status"] == "has_audio"
    assert summary["audio_provider"] == "OpenAI"
    assert summary["audio_model"] == "gpt-4o-mini-tts"
    assert summary["audio_voice"] == "coral"
    assert summary["audio_voice_label"] == "Coral"
    assert summary["audio_generated_at"] == "2026-08-03T10:48:00"
