import json

import pytest

from src.ai.prompts import (
    build_batch_grammar_cards_prompt,
    build_sentence_based_cards_batch_prompt,
    build_vocabulary_batch_prompt,
)
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


def test_provided_examples_batch_prompt_preserves_target_sentence_pairs() -> None:
    prompt = build_sentence_based_cards_batch_prompt(
        [
            "covering letter | I sent in my CV and a covering letter.",
            "career path | Insurance is the career path I intend to pursue.",
        ],
        "English",
        "Polish",
    )

    assert "EXACTLY 2" in prompt
    assert 'target="covering letter" | sentence="I sent in my CV and a covering letter."' in prompt
    assert 'target="career path" | sentence="Insurance is the career path I intend to pursue."' in prompt
    assert "NEVER mix a target with another input's sentence" in prompt


def test_openai_compatible_provided_examples_batch_uses_one_generation_call() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    calls = []
    payload = {
        "cards": [
            _raw_card(
                "covering letter",
                "I sent in my CV and a covering letter.",
            ),
            _raw_card(
                "career path",
                "Insurance is the career path I intend to pursue.",
            ),
        ]
    }

    def fake_generate_text(prompt: str, workflow: str = "card") -> str:
        calls.append((prompt, workflow))
        return json.dumps(payload)

    client._generate_text = fake_generate_text  # type: ignore[method-assign]

    cards = client.generate_sentence_cards_batch(
        [
            "covering letter | I sent in my CV and a covering letter.",
            "career path | Insurance is the career path I intend to pursue.",
        ],
        "English",
        "Polish",
    )

    assert len(calls) == 1
    assert [card.word_or_phrase for card in cards] == [
        "covering letter",
        "career path",
    ]


def test_openai_compatible_provided_examples_batch_rejects_target_mixup() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    payload = {
        "cards": [
            _raw_card(
                "career path",
                "I sent in my CV and a covering letter.",
            ),
            _raw_card(
                "covering letter",
                "Insurance is the career path I intend to pursue.",
            ),
        ]
    }
    client._generate_text = lambda prompt, workflow="card": json.dumps(payload)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="invalid Provided-example batch data"):
        client.generate_sentence_cards_batch(
            [
                "covering letter | I sent in my CV and a covering letter.",
                "career path | Insurance is the career path I intend to pursue.",
            ],
            "English",
            "Polish",
        )


def _raw_grammar(target: str, example: str) -> dict[str, object]:
    return {
        "target": target,
        "structure": f"{target} + clause",
        "rule": f"Use {target} in the requested grammar construction.",
        "example": example,
        "explanation": f"Learner explanation for {target}.",
        "example_demonstrates_structure": True,
        "target_is_structure": True,
    }


def test_grammar_batch_prompt_preserves_order_and_per_item_context() -> None:
    prompt = build_batch_grammar_cards_prompt(
        ["though", "used to"],
        "English",
        ["contrast/concession source", "past-habit source"],
        "Polish",
    )

    assert "exactly 2 grammar learning items" in prompt
    assert "ITEM 1" in prompt
    assert "though" in prompt
    assert "contrast/concession source" in prompt
    assert "ITEM 2" in prompt
    assert "used to" in prompt
    assert "past-habit source" in prompt
    assert '"cards"' in prompt


def test_openai_compatible_grammar_batch_uses_one_generation_call() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    calls = []
    payload = {
        "cards": [
            _raw_grammar("though", "Though it was raining, we went out."),
            _raw_grammar("used to", "I used to live near the sea."),
        ]
    }

    def fake_generate_text(prompt: str, workflow: str = "card") -> str:
        calls.append((prompt, workflow))
        return json.dumps(payload)

    client._generate_text = fake_generate_text  # type: ignore[method-assign]

    cards = client.generate_grammar_cards_batch(
        ["though", "used to"],
        "English",
        ["source: concession", "source: past habit"],
        explanation_language="Polish",
    )

    assert len(calls) == 1
    assert calls[0][1] == "import"
    assert [card.target for card in cards] == ["though", "used to"]
    assert cards[0].sentence == "Though it was raining, we went out."
    assert cards[1].sentence == "I used to live near the sea."


def test_openai_compatible_grammar_batch_rejects_wrong_card_count() -> None:
    client = OpenAiVocabularyClient.__new__(OpenAiVocabularyClient)
    payload = {
        "cards": [
            _raw_grammar("though", "Though it was raining, we went out."),
        ]
    }
    client._generate_text = lambda prompt, workflow="card": json.dumps(payload)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="invalid grammar batch data"):
        client.generate_grammar_cards_batch(
            ["though", "used to"],
            "English",
            ["", ""],
            explanation_language="Polish",
        )
