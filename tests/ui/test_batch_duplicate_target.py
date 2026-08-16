import sys
import types

# modern_gui needs CustomTkinter only when the real UI is instantiated. These
# duplicate-key tests exercise pure helpers and intentionally avoid GUI setup.
sys.modules.setdefault("customtkinter", types.ModuleType("customtkinter"))

from src.ui.modern_gui import ModernVocabularyGui
from src.anki.templates import MODEL_NAME


def test_vocabulary_source_sentence_uses_stored_target_only() -> None:
    item = {
        "word": "echo chamber | Social media can create an echo chamber.",
        "batch_mode": "Provided examples",
        "provided_target": "echo chamber",
        "provided_sentence": "Social media can create an echo chamber.",
    }

    assert ModernVocabularyGui._batch_duplicate_target_for_item(item) == "echo chamber"


def test_pipe_row_uses_left_side_as_word_key() -> None:
    item = {
        "word": "confirmation bias | Confirmation bias affects everyone.",
        "batch_mode": "Provided examples",
    }

    assert ModernVocabularyGui._batch_duplicate_target_for_item(item) == "confirmation bias"


def test_tab_row_uses_left_side_as_word_key() -> None:
    item = {
        "word": "filter bubble\tA filter bubble narrows what you see.",
        "batch_mode": "Vocabulary",
    }

    assert ModernVocabularyGui._batch_duplicate_target_for_item(item) == "filter bubble"


def test_plain_vocabulary_uses_full_phrase_as_word_key() -> None:
    item = {
        "word": "take something with a pinch of salt",
        "batch_mode": "Vocabulary",
    }

    assert (
        ModernVocabularyGui._batch_duplicate_target_for_item(item)
        == "take something with a pinch of salt"
    )


def test_sentence_only_provided_example_is_not_compared_to_word_field_before_generation() -> None:
    item = {
        "word": "Social media can create an echo chamber.",
        "batch_mode": "Provided examples",
    }

    assert ModernVocabularyGui._batch_duplicate_target_for_item(item) == ""


def test_generated_word_is_only_fallback_for_sentence_only_provided_example_after_generation() -> None:
    item = {
        "word": "Social media can create an echo chamber.",
        "batch_mode": "Provided examples",
    }

    assert (
        ModernVocabularyGui._batch_duplicate_target_for_item(
            item,
            generated_word="echo chamber",
        )
        == "echo chamber"
    )


def test_original_target_wins_over_generated_word_for_post_generation_checks() -> None:
    item = {
        "word": "echo chamber | Social media can create an echo chamber.",
        "batch_mode": "Provided examples",
        "provided_target": "echo chamber",
        "duplicate_target": "echo chamber",
    }

    assert (
        ModernVocabularyGui._batch_duplicate_target_for_item(
            item,
            generated_word="an echo chamber",
        )
        == "echo chamber"
    )


def test_grammar_keeps_separate_sentence_duplicate_logic() -> None:
    item = {
        "word": "Not only ... but also | Not only does it matter, but it also helps.",
        "batch_mode": "Grammar",
    }

    assert ModernVocabularyGui._batch_duplicate_target_for_item(item) == ""


def test_precheck_finds_existing_word_before_ai_for_target_plus_sentence() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._batch_items = [
        {
            "word": "echo chamber | Social media can create an echo chamber.",
            "batch_mode": "Provided examples",
            "provided_target": "echo chamber",
            "status": "pending",
        }
    ]
    existing_map = {
        "echo chamber": {
            "note_id": 123,
            "model": MODEL_NAME,
            "word": "echo chamber",
            "duplicate_count": 1,
        }
    }

    duplicate_found = gui._precheck_one_batch_duplicate(0, existing_map, reason="before generation")

    assert duplicate_found is True
    assert gui._batch_items[0]["status"] == "duplicate_found"
    assert gui._batch_items[0]["duplicate_target"] == "echo chamber"
    assert gui._batch_items[0]["duplicate_lookup_value"] == "echo chamber"
    assert "No AI provider API was used" in gui._batch_items[0]["error"]
