from src.ai.prompts import (
    build_multimodal_import_extraction_prompt,
    build_ocr_candidate_extraction_prompt,
    build_smart_grammar_candidate_extraction_prompt,
    build_vocabulary_candidate_extraction_prompt,
)


def test_smart_vocabulary_has_no_fixed_candidate_quota() -> None:
    prompt = build_vocabulary_candidate_extraction_prompt(
        extracted_text="dense lesson",
        target_language="English",
        explanation_language="Polish",
        extraction_mode="Smart vocabulary",
    )
    assert "Candidate count must be driven by the source content" in prompt
    assert "fixed number of candidates" in prompt
    assert "Smart vocabulary <= 80" not in prompt
    assert "keep Vocabulary + source examples <= 60" not in prompt
    assert "Hard output budgets" not in prompt


def test_generic_import_prompt_has_no_fixed_candidate_quota() -> None:
    prompt = build_ocr_candidate_extraction_prompt(
        extracted_text="lesson",
        target_language="Spanish",
        explanation_language="Polish",
        extraction_mode="Mixed",
    )
    assert "Candidate count must be driven by the source content" in prompt
    assert "Keep at most 35 candidates" not in prompt


def test_smart_grammar_has_no_fixed_candidate_quota() -> None:
    prompt = build_smart_grammar_candidate_extraction_prompt(
        extracted_text="grammar lesson",
        target_language="Spanish",
        explanation_language="Polish",
    )
    assert "Candidate count must be driven by the source content" in prompt
    assert "Keep at most 35 candidates" not in prompt


def test_multimodal_import_has_no_fixed_candidate_quota() -> None:
    prompt = build_multimodal_import_extraction_prompt(
        target_language="Spanish",
        explanation_language="Polish",
        extraction_mode="Smart vocabulary",
    )
    assert "Candidate count must be driven by what is actually present on the page" in prompt
    assert "Keep at most 45 candidates" not in prompt
