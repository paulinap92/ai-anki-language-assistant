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


def test_vocabulary_prompt_restores_controlled_recall() -> None:
    prompt = _prompt()

    assert "controlled recall, not runaway word mining" in prompt
    assert "keep reading-text mining minimal and selective" in prompt
    assert "Extract useful reusable collocations and expressions" in prompt
    assert "If the source is mostly continuous prose" in prompt
    assert "prefer quality over quantity" in prompt


def test_vocabulary_prompt_does_not_request_exhaustive_prose_mining() -> None:
    prompt = _prompt()

    assert "scan the ENTIRE remaining document from beginning to end" not in prompt
    assert "Continue through ALL other content-bearing sections" not in prompt


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


def test_smart_vocabulary_prompt_requires_semantic_source_role() -> None:
    prompt = _prompt("Smart vocabulary")

    assert 'source_role="usage_example"' in prompt
    assert 'heading_label' in prompt
    assert 'definition_context' in prompt
    assert 'list_item' in prompt
    assert 'fragment' in prompt
    assert 'exercise' in prompt
    assert '"A PLANNER or SPONTANEOUS"' in prompt
    assert 'must remain type="vocabulary"' in prompt
