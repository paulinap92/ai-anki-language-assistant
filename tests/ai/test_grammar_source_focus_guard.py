import pytest

pytest.importorskip("customtkinter")

from src.domain.models import GrammarAnalysis
from src.ui.modern_gui import ModernVocabularyGui


def test_grammar_source_focus_guard_restores_source_sentence_and_structure():
    item = {
        "word": "used to + base verb | I used to walk to school every day.",
        "grammar_target": "used to + base verb",
        "provided_sentence": "I used to walk to school every day.",
    }
    card = GrammarAnalysis(
        sentence="repeated actions in the past",
        target_language="English",
        meaning="Talking about actions that happened regularly in the past.",
        structure="Use the past simple tense or a past habit form.",
        breakdown=["Past habits"],
        usage="Use it for past habits.",
        context_example="When I was a child, I walked to school.",
        contrasts=["would for repeated past actions"],
        common_mistakes=["I use to walk -> I used to walk"],
    )

    fixed, warnings = ModernVocabularyGui._grammar_card_with_source_focus_guard(item, card)

    assert fixed.sentence == "I used to walk to school every day."
    assert fixed.structure == "used to + base verb"
    assert "audio_sentence_restored_from_source" in warnings
    assert "source_target_restored_in_structure" in warnings


def test_grammar_source_focus_guard_warns_when_generated_sentence_hides_specific_target():
    item = {"word": "used to + base verb", "grammar_target": "used to + base verb"}
    card = GrammarAnalysis(
        sentence="repeated actions in the past",
        target_language="English",
        meaning="Talking about repeated past actions.",
        structure="used to + base verb",
        breakdown=["used to marks a past habit"],
        usage="Use it for past habits that are no longer true.",
        context_example="I used to play tennis after school.",
        contrasts=["past simple can describe single finished actions"],
        common_mistakes=["I use to play -> I used to play"],
    )

    fixed, warnings = ModernVocabularyGui._grammar_card_with_source_focus_guard(item, card)

    assert fixed.sentence == "repeated actions in the past"
    assert "unclear_card_focus_generated_sentence_does_not_show_target" in warnings
