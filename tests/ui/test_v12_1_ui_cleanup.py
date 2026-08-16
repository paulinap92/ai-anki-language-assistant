import sys
import types

sys.modules.setdefault("customtkinter", types.ModuleType("customtkinter"))

from src.ui.modern_gui import ModernVocabularyGui


def test_batch_csv_provided_examples_preserves_target_and_sentence() -> None:
    rows = [
        ["target", "sentence"],
        ["echo chamber", "People can become trapped in an echo chamber."],
    ]
    assert ModernVocabularyGui._batch_rows_from_csv(rows, "Provided examples") == [
        "echo chamber | People can become trapped in an echo chamber."
    ]


def test_batch_csv_vocabulary_uses_only_word_column() -> None:
    rows = [
        ["word", "example"],
        ["echo chamber", "People can become trapped in an echo chamber."],
    ]
    assert ModernVocabularyGui._batch_rows_from_csv(rows, "Vocabulary") == ["echo chamber"]


def test_import_520_is_retryable_and_friendly() -> None:
    exc = RuntimeError("Error code: 520 unknown_origin_error")
    assert ModernVocabularyGui._is_retryable_import_error(exc) is True
    message = ModernVocabularyGui._friendly_import_error_message(exc, "OpenAI")
    assert "temporarily unavailable" in message
    assert "HTTP 520" in message
    assert "preserved" in message
