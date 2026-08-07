"""Conversation Practice helpers."""

from .flashcard_context import (
    build_anki_note_conversation_material,
    build_flashcard_conversation_material,
)
from .selection import (
    SELECTION_ANKI_DUE,
    SELECTION_CONTINUE_ROTATION,
    SELECTION_MODES,
    SELECTION_RANDOM,
    SELECTION_REPEAT_LAST,
    load_rotation_state,
    save_rotation_state,
    select_session_keys,
)
from .suggestions import (
    dedupe_expressions,
    expression_is_grounded_in_exchange,
    expressions_are_near_duplicates,
    filter_new_flashcard_candidates,
    normalize_expression,
)

__all__ = [
    "build_anki_note_conversation_material",
    "build_flashcard_conversation_material",
    "SELECTION_ANKI_DUE",
    "SELECTION_CONTINUE_ROTATION",
    "SELECTION_MODES",
    "SELECTION_RANDOM",
    "SELECTION_REPEAT_LAST",
    "load_rotation_state",
    "save_rotation_state",
    "select_session_keys",
    "dedupe_expressions",
    "expression_is_grounded_in_exchange",
    "expressions_are_near_duplicates",
    "filter_new_flashcard_candidates",
    "normalize_expression",
]
