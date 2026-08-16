from src.ai.prompts import build_ocr_candidate_extraction_prompt


SAMPLE = """
02 · Vocabulary
8 Key Terms
echo chamber
confirmation bias

03 · Facts
The finding may strengthen entrenched beliefs rather than weaken them.

04 · Common Expressions
to cut through the noise

05 · Guided Discussion
Could a selection effect explain the result, or are we digging in because the evidence is uncomfortable?
"""


def _prompt(mode: str = "Vocabulary") -> str:
    return build_ocr_candidate_extraction_prompt(
        extracted_text=SAMPLE,
        target_language="English",
        explanation_language="Polish",
        extraction_mode=mode,
    )


def test_vocabulary_prompt_treats_explicit_lists_as_minimum_not_finish_line() -> None:
    prompt = _prompt()

    assert "guaranteed minimum, not the end of the task" in prompt
    assert "scan the ENTIRE remaining document from beginning to end" in prompt
    assert "discussion questions" in prompt
    assert "advanced C1/C2 material" in prompt
    assert "do not artificially shrink a rich lesson" in prompt


def test_vocabulary_prompt_no_longer_requests_minimal_prose_mining() -> None:
    prompt = _prompt()

    assert "keep reading-text mining minimal" not in prompt
    assert "Extract a small, selective set" not in prompt
    assert "For continuous prose without explicit vocabulary lists" not in prompt
    assert "entrenched beliefs" in prompt
    assert "selection effect" in prompt


def test_vocabulary_modes_keep_their_existing_type_contracts() -> None:
    vocabulary = _prompt("Vocabulary")
    with_examples = _prompt("Vocabulary + source examples")
    smart = _prompt("Smart vocabulary")

    assert 'Use type="vocabulary" for every candidate.' in vocabulary
    assert 'Never return type="provided_example" or type="grammar"' in vocabulary
    assert 'Use type="vocabulary" for every candidate.' in with_examples
    assert 'source examples when they are clearly available' in with_examples
    assert 'may mix vocabulary candidates and provided_example candidates' in smart
    assert 'Never return type="grammar" in Smart vocabulary mode.' in smart
