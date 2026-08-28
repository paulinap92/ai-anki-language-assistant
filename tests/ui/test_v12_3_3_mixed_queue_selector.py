from __future__ import annotations

import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ui.modern_gui import ModernVocabularyGui


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def test_imported_item_types_derive_mixed_queue_mode() -> None:
    items = [
        {"batch_mode": "Provided examples", "mode_locked": True},
        {"batch_mode": "Vocabulary", "mode_locked": True},
        {"batch_mode": "Grammar", "mode_locked": True},
    ]
    assert ModernVocabularyGui._queue_mode_from_imported_item_types(items) == "Mixed"


def test_homogeneous_import_derives_single_queue_mode() -> None:
    items = [
        {"batch_mode": "Provided examples", "mode_locked": True},
        {"batch_mode": "Provided examples", "mode_locked": True},
    ]
    assert ModernVocabularyGui._queue_mode_from_imported_item_types(items) == "Provided examples"


def test_manual_rows_do_not_force_import_mode() -> None:
    items = [
        {"batch_mode": "Vocabulary", "mode_locked": False},
        {"batch_mode": "Grammar", "mode_locked": False},
    ]
    assert ModernVocabularyGui._queue_mode_from_imported_item_types(items) is None


def test_showing_locked_import_item_does_not_replace_mixed_selector() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._batch_items = [
        {
            "word": "bounce back | She bounced back quickly.",
            "batch_mode": "Provided examples",
            "mode_locked": True,
            "status": "pending",
            "source": "ocr_import/AI all text",
        },
        {
            "word": "adaptado de",
            "batch_mode": "Vocabulary",
            "mode_locked": True,
            "status": "pending",
            "source": "ocr_import/AI all text",
        },
    ]
    gui._batch_index = 0
    gui._batch_mode_var = _Var("Mixed")
    gui._batch_topic_var = _Var("")
    gui._batch_word_var = _Var("")
    gui._batch_progress_var = _Var("")
    gui._batch_status_var = _Var("")
    gui._provider_var = _Var("OpenAI")
    gui._batch_generated_card = None
    gui._batch_generated_grammar = None
    gui._batch_generated_provider_name = None
    gui._update_batch_progress = lambda: None
    gui._set_batch_status_card = lambda **kwargs: None
    gui._card_from_batch_payload = lambda payload: None
    gui._grammar_from_batch_payload = lambda payload: None

    gui._show_current_batch_item(generate=False)

    assert gui._batch_mode_var.get() == "Mixed"
    assert gui._batch_mode_for_item(gui._batch_items[0]) == "Provided examples"
    assert gui._batch_mode_for_item(gui._batch_items[1]) == "Vocabulary"
