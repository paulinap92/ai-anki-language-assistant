from src.ai.prompts import (
    build_conversation_feedback_prompt,
    build_conversation_start_prompt,
)


def test_conversation_start_prompt_keeps_normal_topic_mode():
    prompt = build_conversation_start_prompt("travel", "Spanish")

    assert 'Conversation topic: "travel"' in prompt
    assert "FLASHCARD-BASED CONVERSATION MODE" not in prompt


def test_conversation_start_prompt_injects_flashcard_material():
    context = "1. TARGET: dar cuenta de | EXAMPLE: El informe da cuenta de los avances."

    prompt = build_conversation_start_prompt("work", "Spanish", context)

    assert "FLASHCARD-BASED CONVERSATION MODE" in prompt
    assert context in prompt
    assert "realistic opportunity to use 1-3 target items" in prompt


def test_conversation_feedback_prompt_reuses_flashcards():
    context = "1. TARGET: estar abocado a | EXAMPLE: El proyecto está abocado a fracasar."

    prompt = build_conversation_feedback_prompt(
        topic="technology",
        question="¿Qué riesgos ves?",
        answer="Hay muchos riesgos.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
        flashcard_context=context,
    )

    assert context in prompt
    assert "prioritize exact relevant targets" in prompt
    assert '"tutor_reply"' in prompt
    assert "Never ignore a learner's direct question" in prompt


def test_conversation_feedback_prompt_includes_history_and_explain_on_demand_rules():
    context = "1. TARGET: clase magistral | CARD BACK: wykład akademicki"

    prompt = build_conversation_feedback_prompt(
        topic="",
        question="¿Has asistido a una clase magistral?",
        answer="No sé muy bien qué es una clase magistral.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
        flashcard_context=context,
        conversation_history="ai: ¿Has asistido a una clase magistral?",
    )

    assert "RECENT CONVERSATION HISTORY" in prompt
    assert "CARD BACK: wykład akademicki" in prompt
    assert "answer that content question directly" in prompt
    assert "Keep it separate from tutor_reply" in prompt
