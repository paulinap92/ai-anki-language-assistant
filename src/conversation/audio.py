"""Small pure helpers for Conversation Practice spoken output."""

from __future__ import annotations


def build_auto_read_text(
    *,
    tutor_reply: str = "",
    next_question: str = "",
    read_tutor_reply: bool = True,
    read_next_question: bool = True,
) -> str:
    """Combine only the conversational parts selected for automatic TTS."""
    parts: list[str] = []
    if read_tutor_reply and tutor_reply.strip():
        parts.append(tutor_reply.strip())
    if read_next_question and next_question.strip():
        parts.append(next_question.strip())
    return "\n\n".join(parts)
