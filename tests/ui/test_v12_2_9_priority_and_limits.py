from __future__ import annotations

import json
import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ai.prompts import build_vocabulary_candidate_extraction_prompt
from src.ui.modern_gui import ModernVocabularyGui


def test_recommended_accepts_advanced_or_strongly_topic_relevant_learning_value() -> None:
    recommended = {
        "type": "vocabulary",
        "target": "regulatory capture",
        "candidate_kind": "specialist_term",
        "advancedness": "advanced",
        "topic_relevance": "high",
        "reusability": "high",
        "learning_value": "high",
        "document_specificity": "low",
        "confidence": "high",
    }
    normal = dict(recommended, target="setback", advancedness="normal")
    off_topic = dict(recommended, target="vested interests", topic_relevance="low")

    assert ModernVocabularyGui._candidate_review_priority(recommended) == "Recommended"
    assert ModernVocabularyGui._candidate_review_priority(normal) == "Recommended"
    assert ModernVocabularyGui._candidate_review_priority(off_topic) == "Useful"


def test_optional_is_for_weird_document_specific_or_low_reusability_items() -> None:
    assert ModernVocabularyGui._candidate_review_priority(
        {
            "type": "vocabulary",
            "target": "The Phoebus Cartel",
            "document_specificity": "high",
            "reusability": "low",
            "confidence": "high",
        }
    ) == "Optional"
    assert ModernVocabularyGui._candidate_review_priority(
        {
            "type": "vocabulary",
            "target": "attributing complex outcomes to a single cause in this exact policy case",
            "reusability": "low",
            "confidence": "high",
        }
    ) == "Optional"


def test_vocabulary_list_alone_does_not_make_everything_recommended() -> None:
    items = [
        {
            "type": "vocabulary",
            "target": f"term {i}",
            "candidate_kind": "phrase",
            "source_section": "vocabulary_list",
            "confidence": "high",
            "advancedness": "normal",
            "topic_relevance": "medium",
            "reusability": "high",
            "learning_value": "medium",
            "document_specificity": "low",
        }
        for i in range(77)
    ]
    priorities = [ModernVocabularyGui._candidate_review_priority(item) for item in items]
    assert priorities.count("Recommended") == 0
    assert priorities.count("Useful") == 77


def test_source_can_be_blocked_by_number_of_ai_parts_not_only_word_count() -> None:
    # One giant token-like string stays below the old 180k-char hard limit but
    # still creates too many ~20k AI parts, so full-source analysis is blocked.
    text = "x" * 170_000
    assert ModernVocabularyGui._import_source_size_level(text) == "hard"
    summary = ModernVocabularyGui._import_material_size_summary(text)
    assert "Full-source safety limit: 8 AI analysis parts" in summary
    assert "full-source AI search is blocked" in summary


def test_vocabulary_prompt_requests_educational_review_metadata_without_quotas() -> None:
    prompt = build_vocabulary_candidate_extraction_prompt(
        extracted_text="Cronyism and regulatory capture can undermine institutions.",
        target_language="English",
        explanation_language="Polish",
        extraction_mode="Smart vocabulary",
        topic_context="institutions and political systems",
    )
    for field in ("advancedness", "topic_relevance", "reusability", "learning_value", "document_specificity"):
        assert field in prompt
    assert "Do not force a distribution" in prompt
    assert "Never aim for 20, 60, 80, 100" in prompt


def test_ai_candidate_parser_preserves_review_metadata() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "vocabulary",
                    "target": "regulatory capture",
                    "candidate_kind": "specialist_term",
                    "source_section": "reading_text",
                    "confidence": "high",
                    "advancedness": "advanced",
                    "topic_relevance": "high",
                    "reusability": "high",
                    "learning_value": "high",
                    "document_specificity": "low",
                }
            ]
        }
    )
    items = gui._ocr_candidate_items_from_ai_response(raw, default_mode="Smart vocabulary", source="test")
    assert len(items) == 1
    item = items[0]
    assert item["advancedness"] == "advanced"
    assert item["topic_relevance"] == "high"
    assert item["reusability"] == "high"
    assert item["learning_value"] == "high"
    assert item["document_specificity"] == "low"
    assert gui._candidate_review_priority(item) == "Recommended"

class _BoolVar:
    def __init__(self, value=False):
        self.value = bool(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = bool(value)


class _TextVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _priority_item(i: int, priority: str) -> dict[str, str]:
    base = {
        "type": "vocabulary",
        "target": f"candidate {i}",
        "confidence": "high",
        "advancedness": "normal",
        "topic_relevance": "medium",
        "reusability": "high",
        "learning_value": "medium",
        "document_specificity": "low",
    }
    if priority == "Recommended":
        base.update(advancedness="advanced", topic_relevance="high", learning_value="high")
    elif priority == "Optional":
        base.update(document_specificity="high", reusability="low")
    return base


def test_large_review_selects_only_recommended_by_default(monkeypatch) -> None:
    import src.ui.modern_gui as modern_gui

    monkeypatch.setattr(modern_gui.ctk, "BooleanVar", _BoolVar, raising=False)
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._ocr_candidate_status_var = _TextVar("")
    gui._merge_ocr_grammar_candidate_items = lambda items: items
    gui._render_ocr_candidate_cards = lambda: None
    gui._scroll_import_candidates_to_top = lambda: None
    gui._update_ocr_candidate_status = lambda: None

    items = (
        [_priority_item(i, "Recommended") for i in range(8)]
        + [_priority_item(100 + i, "Useful") for i in range(30)]
        + [_priority_item(200 + i, "Optional") for i in range(5)]
    )
    gui._set_ocr_candidate_items(items)

    selected = [var.get() for var in gui._ocr_candidate_vars]
    assert sum(selected) == 8
    assert all(selected[:8])
    assert not any(selected[8:])


def test_small_review_selects_useful_but_not_optional_by_default(monkeypatch) -> None:
    import src.ui.modern_gui as modern_gui

    monkeypatch.setattr(modern_gui.ctk, "BooleanVar", _BoolVar, raising=False)
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._ocr_candidate_status_var = _TextVar("")
    gui._merge_ocr_grammar_candidate_items = lambda items: items
    gui._render_ocr_candidate_cards = lambda: None
    gui._scroll_import_candidates_to_top = lambda: None
    gui._update_ocr_candidate_status = lambda: None

    items = [
        _priority_item(1, "Recommended"),
        _priority_item(2, "Useful"),
        _priority_item(3, "Optional"),
    ]
    gui._set_ocr_candidate_items(items)

    assert [var.get() for var in gui._ocr_candidate_vars] == [True, True, False]
