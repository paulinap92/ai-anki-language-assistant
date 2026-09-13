import sys
import types

import pytest

sys.modules.setdefault("customtkinter", types.ModuleType("customtkinter"))

from src.anki.client import AnkiClient, DuplicateNoteError
from src.anki.templates import GRAMMAR_MODEL_NAME, MODEL_NAME
from src.domain.models import GrammarAnalysis, VocabularyCard
from src.ui.modern_gui import ModernVocabularyGui


def make_vocab(word: str = "echo chamber") -> VocabularyCard:
    return VocabularyCard(
        word_or_phrase=word,
        target_language="English",
        part_of_speech="noun",
        definition="A setting where the same opinions are repeated.",
        translation="bańka informacyjna",
        example="Social media can create an echo chamber.",
        example_translation="Media społecznościowe mogą tworzyć bańkę informacyjną.",
        synonyms=[],
        collocations=[],
        grammar_note="",
    )


def make_grammar(
    target: str = "Third conditional",
    sentence: str = "If I had known, I would have called you.",
    structure: str = "if + past perfect, would have + past participle",
) -> GrammarAnalysis:
    return GrammarAnalysis(
        target=target,
        sentence=sentence,
        target_language="English",
        explanation_language="Polish",
        meaning="Used for unreal past situations and imagined past results.",
        structure=structure,
        breakdown=["if-clause uses past perfect", "result uses would have + participle"],
        usage="Use it to imagine a different past result.",
        context_example=sentence,
        contrasts=[],
        common_mistakes=[],
        target_is_valid=True,
        example_demonstrates_target=True,
    )


class FakeVocabularyCollectionClient(AnkiClient):
    def __init__(self) -> None:
        super().__init__("http://localhost:8765", "Current Deck")
        self.calls: list[tuple[str, dict | None]] = []

    def ensure_vocabulary_model_exists(self) -> None:
        return

    def _invoke(self, action, params=None):  # type: ignore[override]
        self.calls.append((action, params))
        if action == "findNotes":
            # A legacy duplicate exists somewhere else in the collection.
            assert params == {"query": ""}
            return [44]
        if action == "notesInfo":
            return [
                {
                    "noteId": 44,
                    "modelName": "Basic",
                    "tags": [],
                    "fields": {
                        "Front": {"value": "Echo Chamber"},
                        "Back": {"value": "legacy card"},
                    },
                }
            ]
        if action == "addNote":
            raise AssertionError("duplicate must be blocked before addNote")
        return None


def test_vocabulary_final_guard_is_collection_wide_and_blocks_legacy_duplicate() -> None:
    client = FakeVocabularyCollectionClient()

    with pytest.raises(DuplicateNoteError) as exc_info:
        client.add_card(make_vocab(), provider_name="Gemini")

    exc = exc_info.value
    assert exc.note_id == 44
    assert exc.model_name == "Basic"
    assert exc.update_safe is False
    assert all(action != "addNote" for action, _ in client.calls)


class FakeCurrentModelBatchClient(AnkiClient):
    def __init__(self) -> None:
        super().__init__("http://localhost:8765", "Current Deck")
        self.add_called = False

    def ensure_vocabulary_model_exists(self) -> None:
        return

    def find_existing_vocabulary_note_id(self, word_or_phrase: str) -> int | None:  # type: ignore[override]
        assert word_or_phrase == "echo chamber"
        return 88

    def _invoke(self, action, params=None):  # type: ignore[override]
        if action == "addNote":
            self.add_called = True
        return 123


def test_batch_fast_path_still_has_final_duplicate_guard() -> None:
    client = FakeCurrentModelBatchClient()

    with pytest.raises(DuplicateNoteError):
        client.add_card_without_duplicate_scan(make_vocab(), provider_name="Gemini")

    assert client.add_called is False


class FakeGrammarCollectionClient(AnkiClient):
    def __init__(self, existing_target: str, existing_sentence: str) -> None:
        super().__init__("http://localhost:8765", "Current Deck")
        self.existing_target = existing_target
        self.existing_sentence = existing_sentence
        self.queries: list[str] = []
        self.add_called = False

    def ensure_grammar_model_exists(self) -> None:
        return

    def _invoke(self, action, params=None):  # type: ignore[override]
        if action == "findNotes":
            self.queries.append(params["query"])
            return [11]
        if action == "notesInfo":
            return [
                {
                    "noteId": 11,
                    "modelName": GRAMMAR_MODEL_NAME,
                    "fields": {
                        "Target": {"value": self.existing_target},
                        "Sentence": {"value": self.existing_sentence},
                        "Structure": {"value": "if + past perfect, would have + past participle"},
                    },
                }
            ]
        if action == "addNote":
            self.add_called = True
            return 99
        return None


def test_grammar_duplicate_identity_is_target_not_example_sentence() -> None:
    client = FakeGrammarCollectionClient(
        existing_target="Third conditional",
        existing_sentence="If she had left earlier, she would have caught the train.",
    )

    with pytest.raises(DuplicateNoteError):
        client.add_grammar_card(make_grammar(), provider_name="Gemini")

    assert client.add_called is False
    assert client.queries == [f'note:"{GRAMMAR_MODEL_NAME}"']


def test_same_example_sentence_can_belong_to_different_grammar_target() -> None:
    sentence = "If I had known, I would have called you."
    client = FakeGrammarCollectionClient(
        existing_target="Reported speech",
        existing_sentence=sentence,
    )

    client.add_grammar_card(make_grammar(sentence=sentence), provider_name="Gemini")

    assert client.add_called is True


def test_import_candidates_dedupe_same_vocabulary_target_even_with_different_sentences() -> None:
    items = [
        {"type": "vocabulary", "target": "echo chamber", "sentence": "Example one."},
        {"type": "vocabulary", "target": " Echo   Chamber ", "sentence": "Example two."},
    ]

    result = ModernVocabularyGui._dedupe_import_candidate_items(items)

    assert len(result) == 1


def test_import_candidates_dedupe_same_target_first_grammar_card() -> None:
    items = [
        {"type": "grammar", "target": "Third conditional", "sentence": "If I had known, I would have called."},
        {"type": "grammar", "target": "third conditional", "sentence": "If she had left, she would have arrived."},
    ]

    result = ModernVocabularyGui._dedupe_import_candidate_items(items)

    assert len(result) == 1


def test_queue_identity_ignores_source_sentence_for_vocabulary() -> None:
    first = {
        "batch_mode": "Provided examples",
        "word": "echo chamber | Social media can create an echo chamber.",
        "provided_target": "echo chamber",
    }
    second = {
        "batch_mode": "Provided examples",
        "word": "echo chamber | That forum became an echo chamber.",
        "provided_target": "echo chamber",
    }

    assert ModernVocabularyGui._queue_item_identity(first) == ModernVocabularyGui._queue_item_identity(second)


def test_queue_identity_uses_grammar_target_not_example_sentence() -> None:
    first = {
        "batch_mode": "Grammar",
        "word": "Third conditional | If I had known, I would have called.",
        "grammar_target": "Third conditional",
    }
    second = {
        "batch_mode": "Grammar",
        "word": "Third conditional | If she had left, she would have arrived.",
        "grammar_target": "Third conditional",
    }

    assert ModernVocabularyGui._queue_item_identity(first) == ModernVocabularyGui._queue_item_identity(second)


def test_import_vocabulary_and_provided_example_share_one_card_identity() -> None:
    items = [
        {"type": "vocabulary", "target": "echo chamber", "sentence": ""},
        {"type": "provided_example", "target": "echo chamber", "sentence": "That forum became an echo chamber."},
    ]

    result = ModernVocabularyGui._dedupe_import_candidate_items(items)

    assert len(result) == 1


def test_queue_vocabulary_and_provided_example_share_one_card_identity() -> None:
    vocab = {
        "batch_mode": "Vocabulary",
        "word": "echo chamber",
        "provided_target": "echo chamber",
    }
    provided = {
        "batch_mode": "Provided examples",
        "word": "echo chamber | That forum became an echo chamber.",
        "provided_target": "echo chamber",
    }

    assert ModernVocabularyGui._queue_item_identity(vocab) == ModernVocabularyGui._queue_item_identity(provided)


def test_grammar_precheck_blocks_known_target_before_provider_call() -> None:
    class FakeGrammarLookup:
        def find_existing_grammar_note_id(self, target: str):
            assert target == "Third conditional"
            return 555

    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._anki_client = FakeGrammarLookup()
    gui._batch_items = [
        {
            "word": "Third conditional | If I had known, I would have called.",
            "batch_mode": "Grammar",
            "grammar_target": "Third conditional",
            "status": "pending",
        }
    ]

    duplicate_found = gui._precheck_one_batch_duplicate(0, existing_map={}, reason="before generation")

    assert duplicate_found is True
    assert gui._batch_items[0]["status"] == "duplicate_found"
    assert gui._batch_items[0]["duplicate_precheck_scope"] == "all_decks_grammar_target"
    assert "No AI provider API was used" in gui._batch_items[0]["error"]
