from src.ai.prompts import build_vocabulary_prompt


def test_vocabulary_prompt_can_include_topic_context() -> None:
    prompt = build_vocabulary_prompt(
        "generous",
        "English",
        "Polish",
        "character / personality traits",
    )

    assert "Topic / section rules" in prompt
    assert "character / personality traits" in prompt
    assert "hard constraint" in prompt


def test_vocabulary_prompt_without_topic_keeps_default_flow() -> None:
    prompt = build_vocabulary_prompt("generous", "English", "Polish")

    assert "Topic / section rules" not in prompt
    assert '"word_or_phrase": "generous"' in prompt
