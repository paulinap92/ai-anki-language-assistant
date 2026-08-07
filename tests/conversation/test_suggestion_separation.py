from src.conversation import (
    dedupe_expressions,
    expression_is_grounded_in_exchange,
    expressions_are_near_duplicates,
    filter_new_flashcard_candidates,
)


def test_exact_target_is_not_a_new_candidate_even_with_case_or_punctuation():
    candidates = ["Clase magistral!", "la clase magistral"]

    result = filter_new_flashcard_candidates(
        candidates,
        existing_expressions=["clase magistral"],
        exchange_text="La clase magistral fue interesante.",
    )

    assert result == []


def test_longer_collocation_is_allowed_when_it_adds_learning_value():
    result = filter_new_flashcard_candidates(
        ["impartir una clase magistral"],
        existing_expressions=["clase magistral"],
        exchange_text=(
            "Una clase magistral la imparte un experto. "
            "Puedes decir: impartir una clase magistral."
        ),
    )

    assert result == ["impartir una clase magistral"]


def test_random_candidate_not_grounded_in_exchange_is_rejected():
    result = filter_new_flashcard_candidates(
        ["saber al dedillo", "profundizar en un tema"],
        existing_expressions=["clase magistral"],
        exchange_text="Una clase magistral permite profundizar en un tema concreto.",
    )

    assert result == ["profundizar en un tema"]


def test_staged_candidate_is_not_proposed_again():
    result = filter_new_flashcard_candidates(
        ["profundizar en un tema"],
        staged_expressions=["Profundizar en un tema."],
        exchange_text="Me gustaría profundizar en un tema científico.",
    )

    assert result == []


def test_deduplication_preserves_longer_collocations():
    values = dedupe_expressions(
        ["clase magistral", "La clase magistral", "impartir una clase magistral"]
    )

    assert values == ["clase magistral", "impartir una clase magistral"]
    assert expressions_are_near_duplicates("Clase magistral!", "la clase magistral")


def test_grounding_accepts_conservative_content_word_overlap():
    assert expression_is_grounded_in_exchange(
        "impartir una clase magistral",
        "La imparte una profesora durante una clase magistral.",
    )
