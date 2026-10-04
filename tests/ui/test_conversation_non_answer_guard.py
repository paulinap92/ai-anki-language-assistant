from pathlib import Path


def test_conversation_ui_keeps_same_question_for_non_answer() -> None:
    text = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")

    assert 'answer_status in {"non_answer", "wrong_language", "unclear"}' in text
    assert "feedback.next_question = current_question" in text
    assert "if flashcard_mode and should_advance:" in text
    assert "Answer not counted · same question remains active" in text
    assert '"NEXT QUESTION" if getattr(feedback, "should_advance", True) else "TRY AGAIN"' in text
