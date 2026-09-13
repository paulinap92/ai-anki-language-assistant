from src.ai.prompts import (
    build_batch_grammar_prompt,
    build_grammar_analysis_prompt,
    build_ocr_candidate_extraction_prompt,
)
from src.domain.models import GrammarAnalysis


def test_batch_grammar_prompt_is_target_first_and_uses_support_language():
    prompt = build_batch_grammar_prompt(
        "have with this meaning is a dynamic (action) verb and can be used in continuous tenses.",
        "English",
        explanation_language="Polish",
    )

    assert "TARGET-FIRST" in prompt
    assert '"target"' in prompt
    assert "have as a dynamic verb" in prompt
    assert 'Bad: "Have with this meaning is a dynamic verb."' in prompt
    assert 'Good: "We\'re having dinner at the moment."' in prompt
    assert "Explanation language: Polish" in prompt
    assert '"example_demonstrates_target": true' in prompt


def test_batch_grammar_prompt_rejects_meta_sentence_as_example():
    prompt = build_batch_grammar_prompt("Third conditional", "English")

    assert 'Bad: "Third conditional sentences are used to talk about hypothetical past situations."' in prompt
    assert 'Good: "If I had known about the meeting, I would have joined you."' in prompt
    assert "ONE concrete, natural sentence that actually demonstrates the target" in prompt


def test_sentence_analysis_prompt_keeps_example_but_extracts_short_target():
    sentence = "If I had known, I would have called you."
    prompt = build_grammar_analysis_prompt(sentence, "English", "Polish")

    assert sentence in prompt
    assert "short learner-facing grammar label" in prompt
    assert "compact pattern/formula" in prompt
    assert "Explanation language: Polish" in prompt
    assert '"context_example": "If I had known, I would have called you."' in prompt


def test_smart_grammar_prompt_normalizes_long_rules_to_short_targets():
    prompt = build_ocr_candidate_extraction_prompt(
        extracted_text="have with this meaning is a dynamic verb and can be used in continuous tenses.",
        target_language="English",
        explanation_language="Polish",
        extraction_mode="Smart grammar import",
    )

    assert "SHORT, teachable grammar focus/pattern" in prompt
    assert "have as a dynamic verb" in prompt
    assert "full textbook rule" in prompt


def test_old_grammar_payloads_remain_readable_without_new_target_fields():
    card = GrammarAnalysis(
        sentence="If I had known, I would have called you.",
        target_language="English",
        meaning="Hypothetical past result.",
        structure="if + past perfect, would have + past participle",
        breakdown=["past condition", "hypothetical result"],
        usage="For unreal past situations.",
        context_example="If I had known, I would have called you.",
        contrasts=[],
        common_mistakes=[],
    )

    assert card.target == ""
    assert card.explanation_language == ""
    assert card.target_is_valid is True
    assert card.example_demonstrates_target is True
