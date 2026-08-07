"""Conversation suggestion separation and duplicate filtering.

Topic conversations may freely suggest vocabulary. Flashcard-based conversations
need stricter semantics: existing cards are practice material, while only genuinely
new expressions should be staged as candidate cards.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


# Conservative multilingual function-word set used only for near-duplicate and
# relevance checks. It intentionally does not stem or translate content words.
_EDGE_ARTICLES = {
    "an",
    "the",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "il",
    "lo",
    "gli",
    "i",
    "le",
    "uno",
    "un'",
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "einen",
    "dem",
    "den",
    "des",
    "du",
    "des",
    "les",
    "l",
}

_FUNCTION_WORDS = _EDGE_ARTICLES | {
    "al",
    "del",
    "de",
    "en",
    "por",
    "para",
    "con",
    "sin",
    "sobre",
    "a",
    "y",
    "o",
    "e",
    "u",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "by",
    "und",
    "oder",
    "von",
    "zu",
    "mit",
    "für",
    "auf",
    "im",
    "am",
    "nel",
    "nella",
    "di",
    "da",
    "con",
    "per",
    "et",
    "ou",
    "à",
    "au",
    "aux",
    "avec",
    "pour",
}


def normalize_expression(value: object) -> str:
    """Normalize case, punctuation and whitespace without changing word order."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("’", "'").replace("`", "'")
    # Treat punctuation as separators. Unicode ``\w`` preserves accented letters.
    text = re.sub(r"[^\w']+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip(" '" )


def _tokens(value: object) -> list[str]:
    normalized = normalize_expression(value)
    return normalized.split() if normalized else []


def _edge_article_core(value: object) -> tuple[str, ...]:
    tokens = _tokens(value)
    while tokens and tokens[0] in _EDGE_ARTICLES:
        tokens.pop(0)
    while tokens and tokens[-1] in _EDGE_ARTICLES:
        tokens.pop()
    return tuple(tokens)


def expressions_are_near_duplicates(left: object, right: object) -> bool:
    """Return True for exact/case/punctuation/article-only variants."""
    left_normalized = normalize_expression(left)
    right_normalized = normalize_expression(right)
    if not left_normalized or not right_normalized:
        return False
    if left_normalized == right_normalized:
        return True
    left_core = _edge_article_core(left)
    right_core = _edge_article_core(right)
    return bool(left_core and left_core == right_core)


def dedupe_expressions(values: Iterable[object], *, limit: int | None = None) -> list[str]:
    """Keep readable first occurrences while removing normalized duplicates."""
    result: list[str] = []
    for value in values:
        expression = re.sub(r"\s+", " ", str(value or "")).strip()
        if not expression:
            continue
        if any(expressions_are_near_duplicates(expression, existing) for existing in result):
            continue
        result.append(expression)
        if limit is not None and len(result) >= max(0, int(limit)):
            break
    return result


def expression_is_grounded_in_exchange(candidate: object, exchange_text: object) -> bool:
    """Check that a proposed new card is grounded in the current exchange.

    Exact phrase occurrence is preferred. A conservative content-token overlap
    also accepts useful infinitive/collocation forms such as ``impartir una clase
    magistral`` when the exchange contains ``imparte una clase magistral``.
    """
    candidate_normalized = normalize_expression(candidate)
    exchange_normalized = normalize_expression(exchange_text)
    if not candidate_normalized or not exchange_normalized:
        return False
    if candidate_normalized in exchange_normalized:
        return True

    candidate_content = [
        token for token in _tokens(candidate) if token not in _FUNCTION_WORDS and len(token) > 1
    ]
    if not candidate_content:
        return False
    exchange_tokens = set(_tokens(exchange_text))
    matched = sum(1 for token in candidate_content if token in exchange_tokens)
    if len(candidate_content) == 1:
        return matched == 1
    return matched >= 2 and (matched / len(candidate_content)) >= (2 / 3)


def filter_new_flashcard_candidates(
    candidates: Iterable[object],
    *,
    existing_expressions: Iterable[object] = (),
    staged_expressions: Iterable[object] = (),
    exchange_text: object = "",
    limit: int = 6,
) -> list[str]:
    """Return only grounded, non-duplicate candidates for new flashcards.

    Longer collocations containing an existing target remain valid. Only exact
    or article-only variants are removed, so ``impartir una clase magistral`` is
    allowed when ``clase magistral`` already exists.
    """
    existing = dedupe_expressions(existing_expressions)
    staged = dedupe_expressions(staged_expressions)
    accepted: list[str] = []
    safe_limit = max(0, int(limit))

    for candidate in dedupe_expressions(candidates):
        if any(expressions_are_near_duplicates(candidate, item) for item in existing):
            continue
        if any(expressions_are_near_duplicates(candidate, item) for item in staged):
            continue
        if any(expressions_are_near_duplicates(candidate, item) for item in accepted):
            continue
        if not expression_is_grounded_in_exchange(candidate, exchange_text):
            continue
        accepted.append(candidate)
        if len(accepted) >= safe_limit:
            break
    return accepted
