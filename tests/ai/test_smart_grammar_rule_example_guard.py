import json

import pytest

pytest.importorskip("customtkinter")

from src.ui.modern_gui import ModernVocabularyGui


def test_rule_like_have_text_is_not_treated_as_audio_sentence():
    assert ModernVocabularyGui._ocr_looks_like_rule_explanation(
        "have with this meaning is a stative (non-action) verb and is not used in continuous tenses."
    )


def test_smart_grammar_downgrades_bad_structure_sentence_to_rule(monkeypatch):
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    raw = json.dumps(
        {
            "candidates": [
                {
                    "type": "grammar",
                    "target": "have as a stative verb for possession",
                    "sentence": "have with this meaning is a stative (non-action) verb and is not used in continuous tenses.",
                    "source_type": "structure_sentence",
                    "strategy": "preserve_source_sentence",
                }
            ]
        }
    )

    items = gui._ocr_candidate_items_from_ai_response(raw, default_mode="Smart grammar import", source="text")

    assert len(items) == 1
    assert items[0]["type"] == "grammar"
    assert items[0]["target"] == "have as a stative verb for possession"
    assert items[0].get("sentence", "") == ""
    assert items[0]["source_type"] == "rule"
    assert items[0]["strategy"] == "generated_example_from_rule"
    assert "stative" in items[0]["source_rule"]
