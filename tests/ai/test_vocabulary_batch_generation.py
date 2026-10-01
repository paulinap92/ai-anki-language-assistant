import json

import pytest

from src.ai.prompts import build_vocabulary_batch_prompt
from src.ai.providers.openai_provider import OpenAiVocabularyClient


def _raw_card(word: str, example: str) -> dict[str, object]:
    return {
        "is_valid": True,
        "validation_error": "",
        "suggested_correction": "",
        "explanation_language": "Polish",
        "word_or_phrase": word,
        "target_language": "English",
        "part_of_speech": "phrase",
        "definition": "A clear English definition.",
        "translation": "polskie wyjaśnienie",
        "example": example,
        "example_translation": "polskie tłumaczenie przykładu",
        "synonyms": [],
        "collocations": [],
        "grammar_note": "",
        "topic_fit": "not_applicable",
        "topic_warning": "",
        "quality_warnings": [],
        "used_form_in_example": word,
        "example_uses_target": True,
        "target_usage": "exact",
        "collocation_naturalness": "ok",
        "translation_naturalness": "ok",
    }


def test_batch_prompt_preserves_order_and_requests_exact_count() -> None:
    prompt = build_vocabulary_batch_prompt(
        ["fault tolerance", "load balancer", "traffic spike"],
        "English",
        "Polish",
    )

    assert "EXACTLY 3" in prompt
    assert '1. "fault tolerance"' in prompt
    assert '2. "load balancer"' in prompt
    assert '3. "traffic spike"' in prompt
    assert '"cards"' in prompt


def test_openai_compatible_batch_parses_multiple_cards_from_one_generation_call() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    calls = []

    payload = {
        "cards": [
            _raw_card(
                "fault tolerance",
                "Fault tolerance helps the service continue after a failure.",
            ),
            _raw_card(
                "load balancer",
                "The load balancer distributes requests across several servers.",
            ),
        ]
    }

    def fake_generate_text(prompt: str, workflow: str = "card") -> str:
        calls.append((prompt, workflow))
        return json.dumps(payload)

    client._generate_text = fake_generate_text  # type: ignore[method-assign]

    cards = client.generate_cards_batch(
        ["fault tolerance", "load balancer"],
        "English",
        "Polish",
    )

    assert len(calls) == 1
    assert calls[0][1] == "card"
    assert [card.word_or_phrase for card in cards] == [
        "fault tolerance",
        "load balancer",
    ]


def test_openai_compatible_batch_rejects_reordered_or_replaced_target() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    payload = {
        "cards": [
            _raw_card("load balancer", "The load balancer distributes requests."),
            _raw_card("fault tolerance", "Fault tolerance keeps a service running."),
        ]
    }
    client._generate_text = lambda prompt, workflow="card": json.dumps(payload)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="invalid batch flashcard data"):
        client.generate_cards_batch(
            ["fault tolerance", "load balancer"],
            "English",
            "Polish",
        )
