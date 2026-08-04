"""Build bounded Conversation Practice context from in-memory Batch items."""

from __future__ import annotations

from html import unescape
import re
from typing import Any

from src.domain.models import GrammarAnalysis, VocabularyCard


IGNORED_BATCH_STATUSES = {
    "invalid",
    "error",
    "provider_failed",
    "add_failed",
    "skipped",
}


def _compact(value: object, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _vocabulary_card(payload: object) -> VocabularyCard | None:
    if not isinstance(payload, dict):
        return None
    try:
        return VocabularyCard(**payload)
    except Exception:
        return None


def _grammar_card(payload: object) -> GrammarAnalysis | None:
    if not isinstance(payload, dict):
        return None
    try:
        return GrammarAnalysis(**payload)
    except Exception:
        return None


def _split_target_and_sentence(value: object) -> tuple[str, str]:
    text = _compact(value, limit=1000)
    for separator in ("|", "\t"):
        if separator in text:
            target, sentence = text.split(separator, 1)
            return target.strip(), sentence.strip()
    return text, ""


def _generated_vocabulary_row(card: VocabularyCard) -> tuple[str, str]:
    target = _compact(card.word_or_phrase)
    parts = [f"TARGET: {target}"]
    if card.translation:
        parts.append(f"MEANING: {_compact(card.translation)}")
    if card.definition:
        parts.append(f"DEFINITION: {_compact(card.definition)}")
    if card.example:
        parts.append(f"EXAMPLE: {_compact(card.example)}")
    collocations = [_compact(value, limit=80) for value in card.collocations[:4]]
    collocations = [value for value in collocations if value]
    if collocations:
        parts.append(f"COLLOCATIONS: {', '.join(collocations)}")
    return target, " | ".join(parts)


def _generated_grammar_row(
    item: dict[str, Any],
    card: GrammarAnalysis,
) -> tuple[str, str]:
    target = _compact(item.get("grammar_target") or card.structure or item.get("word"))
    parts = [f"GRAMMAR TARGET: {target}"]
    if card.meaning:
        parts.append(f"MEANING: {_compact(card.meaning)}")
    if card.sentence:
        parts.append(f"EXAMPLE: {_compact(card.sentence)}")
    if card.usage:
        parts.append(f"USE: {_compact(card.usage)}")
    return target, " | ".join(parts)


def _pending_row(item: dict[str, Any]) -> tuple[str, str]:
    raw_word = _compact(item.get("word"), limit=1000)
    mode = str(item.get("resolved_mode") or item.get("batch_mode") or "").strip()
    target = raw_word
    sentence = _compact(item.get("provided_sentence"))

    if mode == "Provided examples":
        parsed_target, parsed_sentence = _split_target_and_sentence(raw_word)
        target = _compact(item.get("provided_target") or parsed_target or raw_word)
        sentence = sentence or _compact(parsed_sentence)
    elif mode == "Grammar":
        parsed_target, parsed_sentence = _split_target_and_sentence(raw_word)
        target = _compact(item.get("grammar_target") or parsed_target or raw_word)
        sentence = sentence or _compact(parsed_sentence)

    parts = [f"TARGET: {target}"]
    if sentence:
        parts.append(f"SOURCE EXAMPLE: {sentence}")
    source_rule = _compact(item.get("source_rule"))
    if source_rule:
        parts.append(f"SOURCE NOTE: {source_rule}")
    return target, " | ".join(parts)


def build_flashcard_conversation_material(
    batch_items: list[dict[str, object]],
    *,
    limit: int = 30,
) -> tuple[list[str], list[str], int]:
    """Return prompt rows, visible targets, and total usable unique items.

    The function uses only the current in-memory Batch / Queue payload. It never
    queries AnkiConnect. Generated cards provide richer context; pending rows
    still provide their target and source sentence when available.
    """
    rows: list[str] = []
    targets: list[str] = []
    seen: set[str] = set()
    total = 0
    safe_limit = max(1, int(limit))

    for item in batch_items:
        status = str(item.get("status") or "pending")
        if status in IGNORED_BATCH_STATUSES:
            continue

        vocabulary = _vocabulary_card(item.get("card"))
        grammar = _grammar_card(item.get("grammar_card"))
        if vocabulary is not None:
            target, row = _generated_vocabulary_row(vocabulary)
        elif grammar is not None:
            target, row = _generated_grammar_row(item, grammar)
        else:
            target, row = _pending_row(item)

        if not target:
            continue
        key = target.casefold()
        if key in seen:
            continue
        seen.add(key)
        total += 1
        if len(rows) < safe_limit:
            rows.append(row)
            targets.append(target)

    return rows, targets, total


def _plain_field(value: object, limit: int = 220) -> str:
    """Return compact plain text from an Anki field value."""
    raw = unescape(str(value or ""))
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return _compact(raw, limit=limit)


def _first_anki_field(fields: dict[str, object], names: tuple[str, ...]) -> str:
    for name in names:
        value = _plain_field(fields.get(name))
        if value:
            return value
    return ""


def build_anki_note_conversation_material(
    notes: list[dict[str, object]],
    *,
    limit: int = 30,
) -> tuple[list[str], list[str], int]:
    """Build Conversation Practice material from notes read from one Anki deck.

    The input is the normalized note summary returned by
    ``AnkiClient.list_notes_for_conversation``. Vocabulary, grammar, and legacy
    Basic-style notes are accepted as long as a recognizable target field exists.
    """
    rows: list[str] = []
    targets: list[str] = []
    seen: set[str] = set()
    total = 0
    safe_limit = max(1, int(limit))

    for note in notes:
        fields_raw = note.get("fields")
        fields = fields_raw if isinstance(fields_raw, dict) else {}
        model = str(note.get("model") or "")

        grammar_like = (
            "grammar" in model.casefold()
            or bool(_plain_field(fields.get("Structure")))
            or bool(_plain_field(fields.get("Usage")))
        )

        if grammar_like:
            target = _first_anki_field(
                fields,
                ("Structure", "Sentence", "Expression", "Phrase", "Front"),
            ) or _plain_field(note.get("word"))
            parts = [f"GRAMMAR TARGET: {target}"] if target else []
            meaning = _first_anki_field(fields, ("Meaning", "Translation", "TranslationPL"))
            example = _first_anki_field(fields, ("ContextExample", "Sentence", "Example", "Back"))
            usage = _first_anki_field(fields, ("Usage", "GrammarNote"))
            if meaning:
                parts.append(f"MEANING: {meaning}")
            if example and example.casefold() != target.casefold():
                parts.append(f"EXAMPLE: {example}")
            if usage:
                parts.append(f"USE: {usage}")
        else:
            target = _first_anki_field(
                fields,
                ("Word", "Expression", "Phrase", "Term", "Front", "Sentence"),
            ) or _plain_field(note.get("word"))
            parts = [f"TARGET: {target}"] if target else []
            meaning = _first_anki_field(fields, ("Translation", "TranslationPL", "Meaning"))
            definition = _first_anki_field(fields, ("Definition",))
            explicit_example = _first_anki_field(
                fields,
                ("Example", "ContextExample", "ExampleSentence", "Sentence"),
            ) or _plain_field(note.get("example"))
            example_translation = _first_anki_field(
                fields,
                ("ExampleTranslation", "ExamplePL"),
            )
            card_back = _plain_field(fields.get("Back"))
            collocations = _first_anki_field(fields, ("Collocations", "UsefulPhrases"),)
            grammar_note = _first_anki_field(fields, ("GrammarNote", "Usage"))
            if meaning:
                parts.append(f"MEANING: {meaning}")
            if definition:
                parts.append(f"DEFINITION: {definition}")
            if explicit_example and explicit_example.casefold() != target.casefold():
                parts.append(f"EXAMPLE: {explicit_example}")
            if example_translation:
                parts.append(f"EXAMPLE MEANING: {example_translation}")
            # A generic Basic note usually stores translation/definition on Back.
            # Do not mislabel it as an example; preserve it as authoritative card content.
            if card_back and card_back.casefold() != target.casefold():
                already_present = {
                    value.casefold()
                    for value in (meaning, definition, explicit_example, example_translation)
                    if value
                }
                if card_back.casefold() not in already_present:
                    parts.append(f"CARD BACK: {card_back}")
            if collocations:
                parts.append(f"COLLOCATIONS: {collocations}")
            if grammar_note:
                parts.append(f"USAGE: {grammar_note}")

        if not target or not parts:
            continue
        key = target.casefold()
        if key in seen:
            continue
        seen.add(key)
        total += 1
        if len(rows) < safe_limit:
            rows.append(" | ".join(parts))
            targets.append(target)

    return rows, targets, total

