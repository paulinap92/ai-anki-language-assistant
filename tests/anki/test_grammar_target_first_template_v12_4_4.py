from src.anki.field_builder import GrammarFieldBuilder
from src.anki.templates import GRAMMAR_BACK_TEMPLATE, GRAMMAR_FRONT_TEMPLATE, GRAMMAR_MODEL_FIELDS
from src.domain.models import GrammarAnalysis


def _card() -> GrammarAnalysis:
    return GrammarAnalysis(
        target="Third conditional",
        sentence="If I had known about the meeting, I would have joined you.",
        target_language="English",
        explanation_language="Polish",
        meaning="Nierealna sytuacja w przeszłości i jej hipotetyczny skutek.",
        structure="if + past perfect, would/could/might have + past participle",
        breakdown=["if-clause: past perfect", "result: would have + participle"],
        usage="Do mówienia o przeszłości, której nie można już zmienić.",
        context_example="If I had known about the meeting, I would have joined you.",
        contrasts=["Second conditional -> present/future hypothetical"],
        common_mistakes=["If I would have known -> If I had known"],
    )


def test_grammar_note_has_target_and_explanation_language_fields():
    assert "Target" in GRAMMAR_MODEL_FIELDS
    assert "ExplanationLanguage" in GRAMMAR_MODEL_FIELDS

    fields = GrammarFieldBuilder.build_fields(_card())
    assert fields["Target"] == "Third conditional"
    assert fields["Sentence"].startswith("If I had known")
    assert fields["ContextExample"] == fields["Sentence"]
    assert fields["ExplanationLanguage"] == "Polish"


def test_grammar_front_is_target_first_not_sentence_first():
    assert "{{Target}}" in GRAMMAR_FRONT_TEMPLATE
    assert "{{Sentence}}" not in GRAMMAR_FRONT_TEMPLATE
    assert "{{Structure}}" in GRAMMAR_FRONT_TEMPLATE  # fallback for legacy notes


def test_grammar_back_displays_one_main_example_and_no_competing_context_block():
    assert '<div class="label">Example</div>' in GRAMMAR_BACK_TEMPLATE
    assert '<div class="sentence">{{Sentence}}</div>' in GRAMMAR_BACK_TEMPLATE
    assert "{{ContextExample}}" not in GRAMMAR_BACK_TEMPLATE
    assert '<div class="label">Pattern</div>' in GRAMMAR_BACK_TEMPLATE
