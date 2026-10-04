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


def test_correction_kind_distinguishes_error_improvement_and_stt_issue():
    payload = _base_payload()
    payload["corrections"] = [
        {
            "kind": "error",
            "original": "entre mucho aire",
            "correction": "entra mucho aire",
            "explanation": "Verbo incorrecto.",
        },
        {
            "kind": "improvement",
            "original": "se utiliza para trabajar",
            "correction": "se puede utilizar tanto para trabajar como...",
            "explanation": "La original ya es correcta; esta versión es más elaborada.",
        },
        {
            "kind": "possible_transcription",
            "original": "anrobe",
            "correction": "Land Rover",
            "explanation": "Probable error de reconocimiento de voz.",
        },
    ]

    feedback = ConversationFeedback(**payload)

    assert [item.kind for item in feedback.corrections] == [
        "error",
        "improvement",
        "possible_transcription",
    ]


def test_answer_status_defaults_keep_legacy_outputs_compatible():
    feedback = ConversationFeedback(**_base_payload())

    assert feedback.answer_status == "valid_answer"
    assert feedback.should_advance is True


def test_non_answer_turn_control_fields_are_parsed():
    payload = _base_payload()
    payload.update(
        {
            "answer_status": "non_answer",
            "should_advance": False,
            "corrected_version": "",
            "advanced_answer": "",
        }
    )

    feedback = ConversationFeedback(**payload)

    assert feedback.answer_status == "non_answer"
    assert feedback.should_advance is False
