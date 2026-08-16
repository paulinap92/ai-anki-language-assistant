from datetime import datetime
from pathlib import Path

from src.conversation.audio import build_auto_read_text
from src.conversation.export import (
    default_conversation_export_name,
    render_conversation_markdown,
    render_conversation_text,
    write_conversation_export,
)


def test_auto_read_combines_tutor_reply_and_question_without_feedback():
    text = build_auto_read_text(
        tutor_reply="Entiendo. Es un coche muy robusto.",
        next_question="¿Qué restaurarías primero?",
        read_tutor_reply=True,
        read_next_question=True,
    )

    assert text == "Entiendo. Es un coche muy robusto.\n\n¿Qué restaurarías primero?"


def test_auto_read_can_read_only_the_question():
    assert build_auto_read_text(
        tutor_reply="Respuesta del tutor.",
        next_question="¿Y tú?",
        read_tutor_reply=False,
        read_next_question=True,
    ) == "¿Y tú?"


def test_markdown_export_keeps_metadata_transcript_and_flashcards():
    content = render_conversation_markdown(
        [("YOU", "Tengo un Land Rover."), ("AI TUTOR", "Qué interesante.")],
        metadata={"Language": "Spanish", "Topic": "coches clásicos"},
        session_flashcards=["restaurar", "estar homologado"],
        new_candidates=["aislamiento térmico"],
    )

    assert "# Conversation Practice export" in content
    assert "**Language:** Spanish" in content
    assert "## Session flashcards (2)" in content
    assert "### YOU" in content
    assert "aislamiento térmico" in content


def test_text_export_writes_utf8_file(tmp_path: Path):
    path = tmp_path / "conversation.txt"
    write_conversation_export(
        path,
        [("NEXT QUESTION", "¿Qué harías?")],
        metadata={"Language": "Spanish"},
    )

    content = path.read_text(encoding="utf-8")
    assert "AI ANKI LANGUAGE ASSISTANT" in content
    assert "¿Qué harías?" in content


def test_default_export_name_contains_topic_and_timestamp():
    name = default_conversation_export_name(
        language="Spanish",
        topic="coches clásicos",
        now=datetime(2026, 8, 8, 13, 45),
    )

    assert name == "conversation_coches_clásicos_2026-08-08_1345.md"
