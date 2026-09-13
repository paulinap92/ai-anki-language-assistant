import json
import pytest

from src.ai.base import VocabularyAiClient
from src.ai.prompts import build_batch_grammar_prompt


def _parse(payload: dict):
    return VocabularyAiClient._parse_grammar_analysis(json.dumps(payload), "Test")


def test_prompt_uses_exact_strict_grammar_contract():
    prompt = build_batch_grammar_prompt("Third conditional", "English", explanation_language="Polish")
    for key in (
        '"target"', '"structure"', '"rule"', '"example"', '"explanation"',
        '"example_demonstrates_structure"', '"target_is_structure"',
    ):
        assert key in prompt
    assert "Third conditional sentences are used to talk about unreal past situations." in prompt
    assert "If I had known about the meeting, I would have joined you." in prompt
    assert "Explanation language: Polish" in prompt


def test_regression_rejects_rule_sentence_used_as_example():
    bad = {
        "target": "Third conditional",
        "structure": "if + past perfect, would have + past participle",
        "rule": "Used for unreal past situations.",
        "example": "Third conditional sentences are used to talk about unreal past situations.",
        "explanation": "Opis konstrukcji.",
        "example_demonstrates_structure": False,
        "target_is_structure": True,
    }
    with pytest.raises(ValueError):
        _parse(bad)


def test_regression_rejects_rule_used_as_target():
    bad = {
        "target": "have with this meaning is a dynamic (action) verb and can be used in continuous tenses",
        "structure": "have + activity/experience -> continuous form possible",
        "rule": "Dynamic have can appear in continuous tenses.",
        "example": "We're having dinner at the moment.",
        "explanation": "Tutaj have opisuje czynność.",
        "example_demonstrates_structure": True,
        "target_is_structure": False,
    }
    with pytest.raises(ValueError):
        _parse(bad)


def test_accepts_have_as_dynamic_verb_regression_case():
    good = {
        "target": "have as a dynamic verb",
        "structure": "have + activity/experience -> continuous form possible",
        "rule": "When have describes an activity or experience rather than possession, it can be used in continuous tenses.",
        "example": "We're having dinner at the moment.",
        "explanation": "Tutaj have opisuje czynność, więc forma continuous jest możliwa.",
        "example_demonstrates_structure": True,
        "target_is_structure": True,
    }
    card = _parse(good)
    assert card.target == "have as a dynamic verb"
    assert card.structure == "have + activity/experience -> continuous form possible"
    assert card.sentence == "We're having dinner at the moment."
    assert card.meaning == good["rule"]
    assert card.breakdown == [good["explanation"]]


def test_rejects_missing_self_check_fields():
    payload = {
        "target": "Third conditional",
        "structure": "if + past perfect, would have + past participle",
        "rule": "Used for unreal past situations.",
        "example": "If I had known, I would have called you.",
        "explanation": "Wyjaśnienie.",
    }
    with pytest.raises(ValueError):
        _parse(payload)
