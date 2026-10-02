import random

from src.practice.service import PracticeService


def _field(value: str) -> dict[str, str]:
    return {"value": value}


def test_current_grammar_card_uses_target_as_answer_and_sentence_as_prompt() -> None:
    cards = [
        {
            "note": 101,
            "modelName": PracticeService.GRAMMAR_MODEL,
            "fields": {
                "Target": _field("though"),
                "Sentence": _field("Though it was late, we kept working."),
                "ContextExample": _field("Though it was late, we kept working."),
                "Structure": _field("though + clause"),
                "Meaning": _field("concession"),
                "Usage": _field("Use it to show contrast."),
            },
        },
        {
            "note": 102,
            "modelName": PracticeService.GRAMMAR_MODEL,
            "fields": {
                "Target": _field("because"),
                "Sentence": _field("We stayed inside because it was raining."),
                "ContextExample": _field("We stayed inside because it was raining."),
                "Structure": _field("because + clause"),
                "Meaning": _field("reason"),
                "Usage": _field("Use it to give a reason."),
            },
        },
    ]

    items = PracticeService.from_anki_cards(cards)
    question = PracticeService.build_questions(
        items,
        shuffle=False,
        rng=random.Random(0),
    )[0]

    assert items[0].answer == "though"
    assert items[0].example == "Though it was late, we kept working."
    assert "Though it was late, we kept working." in question.prompt
    assert question.correct_answer == "though"
    assert "though" in question.options
    assert "because" in question.options
    assert "Subordinating conjunction" not in " ".join(question.options)


def test_legacy_grammar_card_uses_sentence_as_target_and_context_as_prompt() -> None:
    cards = [
        {
            "note": 201,
            "modelName": PracticeService.GRAMMAR_MODEL,
            "fields": {
                "Sentence": _field("though"),
                "ContextExample": _field("Though the task was difficult, she finished it."),
                "Structure": _field(
                    "Subordinating conjunction used to introduce a concessive clause."
                ),
                "Meaning": _field("contrast or concession"),
                "Usage": _field("Use it to introduce a concession."),
            },
        },
        {
            "note": 202,
            "modelName": PracticeService.GRAMMAR_MODEL,
            "fields": {
                "Sentence": _field("therefore"),
                "ContextExample": _field("The road was closed; therefore, we turned back."),
                "Structure": _field(
                    "Connector used to show cause-and-effect relationships."
                ),
                "Meaning": _field("result"),
                "Usage": _field("Use it to introduce a result."),
            },
        },
    ]

    items = PracticeService.from_anki_cards(cards)
    question = PracticeService.build_questions(
        items,
        shuffle=False,
        rng=random.Random(0),
    )[0]

    assert items[0].answer == "though"
    assert items[0].example == "Though the task was difficult, she finished it."
    assert "Though the task was difficult, she finished it." in question.prompt
    assert question.correct_answer == "though"
    assert set(question.options) == {"though", "therefore"}
