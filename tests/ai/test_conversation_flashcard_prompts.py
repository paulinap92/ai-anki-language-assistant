import json

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
    assert '"suggested_vocabulary" must be an empty list' in prompt
    assert '"expressions_to_use_next" must contain 2-4' in prompt
    assert '"new_flashcard_candidates" may contain 0-4' in prompt
    assert "impartir una clase magistral" in prompt
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


def test_topic_feedback_prompt_keeps_normal_suggestion_workflow():
    prompt = build_conversation_feedback_prompt(
        topic="travel",
        question="¿Adónde quieres viajar?",
        answer="Quiero viajar a Perú.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
    )

    assert "TOPIC-MODE VOCABULARY OUTPUT CONTRACT" in prompt
    assert '"suggested_vocabulary" must contain 4' in prompt
    assert '"expressions_to_use_next" and "new_flashcard_candidates" must both be empty' in prompt


def test_flashcard_prompt_forbids_using_next_question_to_seed_candidates():
    prompt = build_conversation_feedback_prompt(
        topic="",
        question="¿Qué es una clase magistral?",
        answer="No estoy segura.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
        flashcard_context="1. TARGET: clase magistral | CARD BACK: wykład akademicki",
    )

    assert "Do not seed a random expression into next_question" in prompt
    assert "Existing flashcard targets are practice material, not new-card suggestions" in prompt


def _extract_prompt_json_example(prompt: str) -> dict[str, object]:
    marker = '{\n  "feedback_language"'
    start = prompt.rfind(marker)
    assert start >= 0
    return json.loads(prompt[start:])


def test_feedback_prompt_json_example_matches_mode_contract():
    topic_prompt = build_conversation_feedback_prompt(
        topic="travel",
        question="¿Adónde quieres viajar?",
        answer="Quiero viajar a Perú.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
    )
    flashcard_prompt = build_conversation_feedback_prompt(
        topic="",
        question="¿Qué es una clase magistral?",
        answer="No lo sé.",
        target_language="Spanish",
        improvement_level="Strong B2/C1",
        feedback_language="Polish",
        flashcard_context="1. TARGET: clase magistral | CARD BACK: wykład akademicki",
    )

    topic_example = _extract_prompt_json_example(topic_prompt)
    flashcard_example = _extract_prompt_json_example(flashcard_prompt)

    assert len(topic_example["suggested_vocabulary"]) == 4
    assert topic_example["expressions_to_use_next"] == []
    assert flashcard_example["suggested_vocabulary"] == []
    assert flashcard_example["expressions_to_use_next"]
    assert flashcard_example["new_flashcard_candidates"]
