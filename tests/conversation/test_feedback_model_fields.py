from src.domain.models import ConversationFeedback


def _base_payload() -> dict[str, object]:
    return {
        "feedback_language": "Polish",
        "feedback": "Dobrze.",
        "corrections": [],
        "corrected_version": "Está bien.",
        "advanced_answer": "Está bastante bien.",
        "mini_practice": "Napisz zdanie.",
        "tutor_reply": "Entiendo.",
        "next_question": "¿Y tú?",
    }


def test_new_conversation_lists_are_optional_for_legacy_provider_output():
    feedback = ConversationFeedback(**_base_payload())

    assert feedback.suggested_vocabulary == []
    assert feedback.expressions_to_use_next == []
    assert feedback.new_flashcard_candidates == []


def test_flashcard_mode_fields_are_parsed_separately():
    payload = _base_payload()
    payload.update(
        {
            "suggested_vocabulary": [],
            "expressions_to_use_next": ["clase magistral"],
            "new_flashcard_candidates": ["impartir una clase magistral"],
        }
    )

    feedback = ConversationFeedback(**payload)

    assert feedback.expressions_to_use_next == ["clase magistral"]
    assert feedback.new_flashcard_candidates == ["impartir una clase magistral"]
