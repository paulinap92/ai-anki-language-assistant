from src.ai.prompts import VOCABULARY_PROMPT_VERSION, build_vocabulary_prompt
from src.domain.models import VocabularyCard
from src.quality import validate_vocabulary_card


def _card(**overrides: object) -> VocabularyCard:
    data = {
        "is_valid": True,
        "validation_error": "",
        "suggested_correction": "",
        "explanation_language": "Polish",
        "word_or_phrase": "nostalgia",
        "target_language": "English",
        "part_of_speech": "noun",
        "definition": "A feeling of longing for the past.",
        "translation_pl": "nostalgia",
        "example": "She felt nostalgia when she saw her old school.",
        "example_pl": "Poczuła nostalgię, kiedy zobaczyła swoją starą szkołę.",
        "synonyms": ["longing"],
        "collocations": ["feel nostalgia"],
        "grammar_note": "Rzeczownik niepoliczalny w wielu kontekstach.",
        "topic_fit": "ok",
        "topic_warning": "",
        "quality_warnings": [],
    }
    data.update(overrides)
    return VocabularyCard(**data)


def test_prompt_v5_includes_user_topic_and_quality_self_check() -> None:
    prompt = build_vocabulary_prompt(
        "generous",
        "English",
        "Polish",
        "character / personality traits",
    )

    assert VOCABULARY_PROMPT_VERSION == "v5-topic-quality-validation"
    assert "User topic/context" in prompt
    assert "character / personality traits" in prompt
    assert "quality_warnings" in prompt
    assert "topic_fit" in prompt
    assert "The user can type any topic" in prompt


def test_prompt_supports_non_polish_explanation_language() -> None:
    prompt = build_vocabulary_prompt("generous", "English", "Spanish", "Mundo laboral")

    assert "Explanation language: Spanish" in prompt
    assert "Spanish must sound natural" in prompt
    assert "Do not use Polish explanations" in prompt
    assert "Mundo laboral" in prompt


def test_validator_catches_polish_cyrillic_and_known_bad_forms() -> None:
    card = _card(
        translation_pl="nostalgja",
        example_pl="To była głęboka smutek i область живота.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="nostalgia",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert any("nostalgja" in warning for warning in warnings)
    assert any("głęboka smutek" in warning for warning in warnings)
    assert any("Cyrillic" in warning for warning in warnings)


def test_validator_respects_spanish_explanation_language() -> None:
    card = _card(
        explanation_language="Spanish",
        translation_pl="hojność",
        example_pl="Ona jest bardzo hojna wobec przyjaciół.",
        grammar_note="Używane jako rzeczownik.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="nostalgia",
        expected_target_language="English",
        expected_explanation_language="Spanish",
    )

    assert any("Polish characters" in warning for warning in warnings)


def test_validator_allows_user_defined_topic_but_surfaces_provider_mismatch() -> None:
    card = _card(
        topic_fit="mismatch",
        topic_warning="The sentence is too generic for the user topic.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="nostalgia",
        expected_target_language="English",
        expected_explanation_language="Polish",
        topic_context="Spanish bureaucracy and appointments",
    )

    assert any("topic fit" in warning or "topic warning" in warning for warning in warnings)
