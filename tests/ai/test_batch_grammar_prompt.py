from src.ai.prompts import build_batch_grammar_prompt
from src.domain.models import GrammarAnalysis


def test_batch_grammar_prompt_contains_structure_and_topic_variety_rules():
    prompt = build_batch_grammar_prompt(
        "aunque + subjuntivo",
        "Spanish",
        "DELE writing / letters / essays",
    )

    assert "aunque + subjuntivo" in prompt
    assert "Target language: Spanish" in prompt
    assert "Do not overuse one noun such as \"ensayo\"" in prompt
    assert '"sentence": "source sentence only if the input contains target | sentence; otherwise aunque + subjuntivo"' in prompt


def test_batch_grammar_model_accepts_prompt_schema_shape():
    card = GrammarAnalysis(
        sentence="aunque + subjuntivo",
        target_language="Spanish",
        meaning="Expresa una concesión o condición no confirmada.",
        structure="aunque + subjuntivo",
        breakdown=["aunque introduce la idea", "subjuntivo marca incertidumbre"],
        usage="Se usa cuando la situación es hipotética o no confirmada.",
        context_example="Aunque sea difícil, enviaré la reclamación formal.",
        contrasts=["aunque + indicativo para hechos conocidos"],
        common_mistakes=["aunque es difícil -> aunque sea difícil cuando es hipotético"],
    )

    assert card.sentence == "aunque + subjuntivo"
    assert card.structure == "aunque + subjuntivo"

from src.ai.prompts import SENTENCE_BASED_CARD_PROMPT_VERSION, build_sentence_based_card_prompt


def test_sentence_based_prompt_preserves_user_sentence():
    prompt = build_sentence_based_card_prompt(
        "come across | I came across an interesting article yesterday.",
        "English",
        "Polish",
        "reading / learning",
    )

    assert SENTENCE_BASED_CARD_PROMPT_VERSION == "v1-provided-example-card"
    assert "Use the provided sentence as the main example" in prompt
    assert "Do NOT replace it with a new invented example" in prompt
    assert "I came across an interesting article yesterday." in prompt
    assert '"example": "I came across an interesting article yesterday."' in prompt


def test_batch_grammar_prompt_keeps_sentence_field_audio_ready_for_target_sentence_rows():
    prompt = build_batch_grammar_prompt(
        "should have / ought to have + past participle | We should have / ought to have driven – it would have been quicker.",
        "English",
        "",
    )

    assert "grammar target | source sentence" in prompt
    assert "put ONLY the source sentence" in prompt
    assert "use the left side as the structure/pattern clue" in prompt
