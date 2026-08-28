from __future__ import annotations

import json
import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ui.modern_gui import ModernVocabularyGui


def test_smart_vocabulary_auto_routes_real_source_usage_to_provided_example() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "vocabulary",
                    "target": "bounce back",
                    "source_sentence": "She bounced back quickly after the setback.",
                    "candidate_kind": "phrasal_verb",
                    "source_section": "reading_text",
                }
            ]
        }
    )

    items = gui._ocr_candidate_items_from_ai_response(raw, default_mode="Smart vocabulary", source="test")

    assert len(items) == 1
    assert items[0]["type"] == "provided_example"
    assert items[0]["target"] == "bounce back"
    assert items[0]["sentence"] == "She bounced back quickly after the setback."
    assert items[0]["source_type"] == "provided_example"
    assert items[0]["strategy"] == "preserve_source_sentence"


def test_smart_vocabulary_keeps_definition_as_vocabulary_context() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "vocabulary",
                    "target": "cronyism",
                    "source_sentence": "The practice of favouring close friends or political allies regardless of merit.",
                    "candidate_kind": "specialist_term",
                }
            ]
        }
    )

    items = gui._ocr_candidate_items_from_ai_response(raw, default_mode="Smart vocabulary", source="test")

    assert len(items) == 1
    assert items[0]["type"] == "vocabulary"
    assert items[0]["sentence"].startswith("The practice of favouring")


def test_smart_vocabulary_definition_that_names_target_still_stays_vocabulary() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "vocabulary",
                    "target": "cronyism",
                    "source_sentence": "Cronyism is the practice of favouring close friends or political allies regardless of merit.",
                }
            ]
        }
    )

    items = gui._ocr_candidate_items_from_ai_response(raw, default_mode="Smart vocabulary", source="test")

    assert len(items) == 1
    assert items[0]["type"] == "vocabulary"


def test_review_priority_can_recommend_strong_topic_item_without_advanced_and_topic_high_both() -> None:
    strong_topic = {
        "type": "vocabulary",
        "target": "systemic failure",
        "candidate_kind": "collocation",
        "advancedness": "normal",
        "topic_relevance": "high",
        "reusability": "high",
        "learning_value": "high",
        "document_specificity": "low",
    }
    advanced_relevant = {
        "type": "vocabulary",
        "target": "regulatory capture",
        "candidate_kind": "specialist_term",
        "advancedness": "advanced",
        "topic_relevance": "medium",
        "reusability": "high",
        "learning_value": "high",
        "document_specificity": "low",
    }

    assert ModernVocabularyGui._candidate_review_priority(strong_topic) == "Recommended"
    assert ModernVocabularyGui._candidate_review_priority(advanced_relevant) == "Recommended"

class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Tabs:
    def __init__(self):
        self.selected = None

    def set(self, value):
        self.selected = value


def test_smart_vocabulary_real_example_reaches_queue_as_provided_example() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "vocabulary",
                    "target": "bounce back",
                    "source_sentence": "She bounced back quickly after the setback.",
                }
            ]
        }
    )
    gui._ocr_candidate_items = gui._ocr_candidate_items_from_ai_response(
        raw, default_mode="Smart vocabulary", source="test"
    )
    gui._ocr_candidate_vars = [_Var(True)]
    gui._batch_topic_var = _Var("")
    gui._language_var = _Var("English")
    gui._explanation_language_var = _Var("Polish")
    gui._batch_mode_var = _Var("Vocabulary")
    gui._batch_mode_help_var = _Var("")
    gui._batch_source_summary_var = _Var("")
    gui._ocr_candidate_status_var = _Var("")
    gui._tabs = _Tabs()
    gui._batch_items = []
    gui._batch_index = 0
    gui._batch_autosave_path = None
    gui._batch_generated_card = None
    gui._batch_generated_provider_name = None
    gui._batch_generated_grammar = None
    gui._show_current_batch_item = lambda generate=False: None
    gui._update_batch_mode_help = lambda: None
    gui._autosave_batch_session = lambda *args, **kwargs: None
    gui._cleanup_runtime_memory = lambda *args, **kwargs: None
    gui._record_activity = lambda *args, **kwargs: None

    gui._send_ocr_candidates_to_batch()

    assert len(gui._batch_items) == 1
    item = gui._batch_items[0]
    assert item["batch_mode"] == "Provided examples"
    assert item["provided_target"] == "bounce back"
    assert item["provided_sentence"] == "She bounced back quickly after the setback."
    assert item["word"] == "bounce back | She bounced back quickly after the setback."
