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

    assert VOCABULARY_PROMPT_VERSION == "v8-language-neutral-schema"
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


def test_validator_allows_normal_polish_diacritics_without_spanish_warning() -> None:
    card = _card(
        translation_pl="inflacja dyplomów; deprecjacja wartości dyplomów",
        example_pl="Ze względu na inflację dyplomów wielu pracodawców wymaga magisterium.",
        grammar_note="Rzeczownik złożony; używany z czasownikami 'pay' lub 'charge'.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="nostalgia",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert not any("Spanish-looking" in warning for warning in warnings)
    assert not any("Spanish-specific" in warning for warning in warnings)
    assert not any("mixed-language text in Polish grammar note" in warning for warning in warnings)


def test_validator_filters_noisy_provider_soft_warnings() -> None:
    card = _card(
        quality_warnings=[
            "SOFT: Spanish-looking characters detected in Polish example translation.",
            "SOFT: possible mixed-language text in Polish grammar note: a, the, on, for.",
        ]
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="nostalgia",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert warnings == []


def test_validator_ignores_outer_quotes_in_exact_input_match() -> None:
    card = _card(word_or_phrase="Nevertheless…")

    warnings = validate_vocabulary_card(
        card,
        expected_input='"Nevertheless…"',
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert not any("input phrase changed" in warning for warning in warnings)


def test_prompt_v7_requires_example_to_use_target_item() -> None:
    prompt = build_vocabulary_prompt("derrumbar(se)", "Spanish", "Polish")

    assert VOCABULARY_PROMPT_VERSION == "v8-language-neutral-schema"
    assert "MUST use the target word/phrase" in prompt
    assert "Do not replace the target with a synonym" in prompt
    assert "used_form_in_example" in prompt
    assert "collocation_naturalness" in prompt
    assert "translation_naturalness" in prompt


def test_validator_blocks_spanish_verb_example_that_uses_synonym() -> None:
    card = _card(
        word_or_phrase="derrumbar(se)",
        target_language="Spanish",
        part_of_speech="verbo transitivo/pronominal",
        definition="Hacer caer o desplomarse una estructura.",
        translation_pl="zawalić się",
        example="El terremoto derribó varios edificios antiguos.",
        example_pl="Trzęsienie ziemi zawaliło kilka starych budynków.",
        grammar_note="Czasownik może być użyty jako pronominalny.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="derrumbar(se)",
        expected_target_language="Spanish",
        expected_explanation_language="Polish",
    )

    assert any("example does not use the target word/phrase" in warning for warning in warnings)


def test_validator_allows_spanish_verb_valid_conjugated_form() -> None:
    card = _card(
        word_or_phrase="encolerizarse",
        target_language="Spanish",
        part_of_speech="verbo pronominal",
        definition="Enfadarse intensamente.",
        translation_pl="wpaść w gniew",
        example="El entrenador se encolerizó cuando vio el comportamiento antideportivo.",
        example_pl="Trener wpadł w gniew, gdy zobaczył niesportowe zachowanie.",
        grammar_note="Czasownik pronominalny: encolerizarse.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="encolerizarse",
        expected_target_language="Spanish",
        expected_explanation_language="Polish",
    )

    assert not any("example does not use the target word/phrase" in warning for warning in warnings)


def test_validator_blocks_spanish_verb_visually_similar_wrong_form() -> None:
    card = _card(
        word_or_phrase="encolerizarse",
        target_language="Spanish",
        part_of_speech="verbo pronominal",
        definition="Enfadarse intensamente.",
        translation_pl="wpaść w gniew",
        example="El entrenador se encolorizó cuando vio el comportamiento antideportivo.",
        example_pl="Trener wpadł w gniew, gdy zobaczył niesportowe zachowanie.",
        grammar_note="Czasownik pronominalny: encolerizarse.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="encolerizarse",
        expected_target_language="Spanish",
        expected_explanation_language="Polish",
    )

    assert any("example does not use the target word/phrase" in warning for warning in warnings)


def test_validator_warns_when_target_is_used_but_collocation_is_awkward() -> None:
    card = _card(
        word_or_phrase="come across",
        target_language="English",
        part_of_speech="phrasal verb",
        definition="To find or meet something by chance.",
        translation_pl="natknąć się na",
        example="We came across some rain during our hike.",
        example_pl="Natknęliśmy się na deszcz podczas wędrówki.",
        grammar_note="Phrasal verb.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="come across",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert any("collocation" in warning and "come across" in warning for warning in warnings)


def test_validator_hard_warns_absurd_collocation_even_if_target_is_present() -> None:
    card = _card(
        word_or_phrase="mesmerizing flow",
        target_language="English",
        part_of_speech="noun phrase",
        definition="A captivating movement or progression.",
        translation_pl="hipnotyzujący przepływ",
        example="The mesmerizing flow of the smoothie caught everyone's attention.",
        example_pl="Hipnotyzujący przepływ smoothie przyciągnął uwagę wszystkich.",
        grammar_note="Noun phrase.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="mesmerizing flow",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert any(warning.startswith("HARD:") and "smoothie" in warning for warning in warnings)


def test_provider_self_check_bad_naturalness_becomes_hard_warning() -> None:
    card = _card(
        word_or_phrase="wear down",
        target_language="English",
        part_of_speech="phrasal verb",
        example="She tried to wear down his doubts.",
        example_pl="Próbowała zmęczyć jego wątpliwości.",
        collocation_naturalness="bad",
        translation_naturalness="bad",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="wear down",
        expected_target_language="English",
        expected_explanation_language="Polish",
    )

    assert any("collocation naturalness as bad" in warning for warning in warnings)
    assert any("translation naturalness as bad" in warning for warning in warnings)


def test_language_neutral_validator_blocks_wrong_similar_form() -> None:
    card = _card(
        word_or_phrase="encolerizarse",
        target_language="Spanish",
        part_of_speech="verb",
        definition="Enfadarse intensamente.",
        translation_pl="wpaść w gniew",
        example="El entrenador se encolorizó cuando vio el comportamiento antideportivo.",
        example_pl="Trener wpadł w gniew, gdy zobaczył niesportowe zachowanie.",
        grammar_note="Czasownik pronominalny.",
    )

    warnings = validate_vocabulary_card(
        card,
        expected_input="encolerizarse",
        expected_target_language="Spanish",
        expected_explanation_language="Polish",
    )

    assert any("target word/phrase" in warning for warning in warnings)


def test_vocabulary_card_accepts_neutral_translation_fields() -> None:
    card = VocabularyCard(
        is_valid=True,
        explanation_language="Spanish",
        word_or_phrase="credential",
        target_language="English",
        part_of_speech="noun",
        translation="credencial",
        definition="A document or qualification that proves identity or competence.",
        example="She earned a teaching credential.",
        example_translation="Obtuvo una credencial docente.",
        synonyms=["certificate"],
        collocations=["teaching credential"],
        grammar_note="Se usa como sustantivo contable.",
    )
    assert card.translation == "credencial"
    assert card.translation_pl == "credencial"
    assert card.example_translation == "Obtuvo una credencial docente."
    assert card.example_pl == "Obtuvo una credencial docente."


def test_prompt_uses_language_neutral_schema_names() -> None:
    prompt = build_vocabulary_prompt("credencial", "Spanish", "English")
    assert '"translation": "string"' in prompt
    assert '"example_translation": "string"' in prompt
    assert '"translation_pl"' not in prompt
    assert '"example_pl"' not in prompt


def test_same_as_target_explanation_language_is_resolved() -> None:
    card = VocabularyCard(
        is_valid=True,
        explanation_language="Spanish",
        word_or_phrase="credencial",
        target_language="Spanish",
        part_of_speech="noun",
        translation="documento que acredita una identidad o cualificación",
        definition="Documento que acredita una identidad o cualificación.",
        example="Presentó su credencial antes del examen.",
        example_translation="Presentó su credencial antes del examen.",
        synonyms=["certificado"],
        collocations=["credencial académica"],
        grammar_note="Sustantivo femenino.",
    )
    warnings = validate_vocabulary_card(
        card,
        expected_input="credencial",
        expected_target_language="Spanish",
        expected_explanation_language="Same as target",
    )
    assert not any("explanation language mismatch" in warning for warning in warnings)
