from src.ai.prompts import build_ocr_candidate_extraction_prompt


def test_smart_grammar_import_prompt_routes_rules_examples_transformations_and_exercises():
    prompt = build_ocr_candidate_extraction_prompt(
        extracted_text="""
        We use have to to express obligation imposed by others.
        used to + base verb | I used to walk to school.
        un hippi -> hippies
        You ___ smoke here. mustn't / don't have to
        """,
        target_language="English",
        explanation_language="Same as target",
        extraction_mode="Smart grammar import",
    )

    assert "Smart grammar import" in prompt
    assert "structure_sentence" in prompt
    assert "generated_example_from_rule" in prompt
    assert "transformation" in prompt
    assert "exercise_draft_review_answer" in prompt
    assert "source_type" in prompt
    assert "source_rule" in prompt
    assert "Never put the rule itself in sentence" in prompt
