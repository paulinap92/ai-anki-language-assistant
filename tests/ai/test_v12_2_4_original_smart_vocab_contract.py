from src.ai.prompts import build_ocr_candidate_extraction_prompt


def _smart_prompt() -> str:
    return build_ocr_candidate_extraction_prompt(
        extracted_text="A lesson with ordinary prose.",
        target_language="English",
        explanation_language="Polish",
        extraction_mode="Smart vocabulary",
        topic_context="",
    )


def test_smart_vocab_uses_controlled_recall_contract_again() -> None:
    prompt = _smart_prompt()
    assert "controlled recall, not runaway word mining" in prompt
    assert "Do NOT extract every possible word from continuous prose" in prompt
    assert "Candidate count must be driven by the source content" in prompt
    assert "Never aim for 20, 60, 80, 100, or any other fixed number" in prompt
    assert "prefer quality over quantity" in prompt
    assert "Smart vocabulary <= 80" not in prompt


def test_smart_vocab_no_longer_requests_exhaustive_whole_document_mining() -> None:
    prompt = _smart_prompt()
    assert "scan the ENTIRE remaining document" not in prompt
    assert "Continue through ALL other content-bearing sections" not in prompt
