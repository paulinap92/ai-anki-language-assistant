"""Local quality validation for generated vocabulary flashcards.

The LLM prompt is useful, but it is not a safety boundary. These checks run
locally after generation and before Anki updates. They intentionally stay
lightweight: they catch obvious language/topic problems and surface warnings for
human review instead of pretending to be a full grammar checker.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.domain.models import VocabularyCard


CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
POLISH_DIACRITICS_RE = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
SPANISH_DIACRITICS_RE = re.compile(r"[áéíóúüñ¿¡ÁÉÍÓÚÜÑ]")
GERMAN_DIACRITICS_RE = re.compile(r"[äöüßÄÖÜ]")
ITALIAN_DIACRITICS_RE = re.compile(r"[àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ]")


KNOWN_QUALITY_PATTERNS: list[tuple[str, str]] = [
    ("nostalgja", "HARD: possible typo: 'nostalgja' → 'nostalgia'."),
    ("głęboka smutek", "HARD: possible Polish grammar error: 'głęboka smutek' → 'głęboki smutek'."),
    ("область живота", "HARD: Cyrillic phrase detected: 'область живота'."),
]


COMMON_POLISH_WORDS = {
    "że", "jest", "nie", "się", "do", "na", "w", "z", "dla", "który", "która",
    "to", "ten", "ta", "tego", "jako", "przez", "po", "lub", "ale", "oraz",
}
COMMON_SPANISH_WORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "que",
    "para", "por", "con", "como", "pero", "más", "muy", "se", "es", "son",
}
COMMON_ENGLISH_WORDS = {
    "the", "a", "an", "to", "of", "and", "or", "but", "with", "for", "from",
    "that", "this", "these", "those", "is", "are", "be", "as", "in", "on",
}
COMMON_GERMAN_WORDS = {
    "der", "die", "das", "und", "oder", "aber", "mit", "für", "von", "zu", "ist", "sind",
}
COMMON_ITALIAN_WORDS = {
    "il", "lo", "la", "gli", "le", "un", "una", "di", "che", "per", "con", "come", "ma", "è", "sono",
}


LANGUAGE_RULES = {
    "polish": {
        "expected_words": COMMON_POLISH_WORDS,
        "unexpected_words": COMMON_SPANISH_WORDS | COMMON_ENGLISH_WORDS | COMMON_GERMAN_WORDS | COMMON_ITALIAN_WORDS,
        "diacritics_re": POLISH_DIACRITICS_RE,
    },
    "spanish": {
        "expected_words": COMMON_SPANISH_WORDS,
        "unexpected_words": COMMON_POLISH_WORDS | COMMON_ENGLISH_WORDS | COMMON_GERMAN_WORDS | COMMON_ITALIAN_WORDS,
        "diacritics_re": SPANISH_DIACRITICS_RE,
    },
    "english": {
        "expected_words": COMMON_ENGLISH_WORDS,
        "unexpected_words": COMMON_POLISH_WORDS | COMMON_SPANISH_WORDS | COMMON_GERMAN_WORDS | COMMON_ITALIAN_WORDS,
        "diacritics_re": re.compile(r"$a"),
    },
    "german": {
        "expected_words": COMMON_GERMAN_WORDS,
        "unexpected_words": COMMON_POLISH_WORDS | COMMON_SPANISH_WORDS | COMMON_ENGLISH_WORDS | COMMON_ITALIAN_WORDS,
        "diacritics_re": GERMAN_DIACRITICS_RE,
    },
    "italian": {
        "expected_words": COMMON_ITALIAN_WORDS,
        "unexpected_words": COMMON_POLISH_WORDS | COMMON_SPANISH_WORDS | COMMON_ENGLISH_WORDS | COMMON_GERMAN_WORDS,
        "diacritics_re": ITALIAN_DIACRITICS_RE,
    },
}


TRANSLATION_FIELDS = (
    ("translation/explanation", "translation_pl"),
    ("example translation", "example_pl"),
    ("grammar note", "grammar_note"),
)


def validate_vocabulary_card(
    card: VocabularyCard,
    *,
    expected_input: str = "",
    expected_target_language: str = "",
    expected_explanation_language: str = "",
    topic_context: str = "",
) -> list[str]:
    """Return local quality warnings for a generated vocabulary card.

    Args:
        card: Generated card returned by a provider.
        expected_input: User input that should be preserved exactly.
        expected_target_language: Target language selected in the UI.
        expected_explanation_language: Explanation/translation language selected in the UI.
        topic_context: User-provided topic/context, if any.

    Returns:
        Human-readable warnings. Warnings prefixed with ``HARD:`` need explicit
        user confirmation before adding/updating Anki.
    """
    warnings: list[str] = []

    _check_required_fields(card, warnings)
    _check_expected_values(
        card,
        warnings,
        expected_input=expected_input,
        expected_target_language=expected_target_language,
        expected_explanation_language=expected_explanation_language,
    )
    _check_explanation_language_fields(card, warnings, expected_explanation_language)
    _check_known_bad_patterns(card, warnings)
    _check_llm_self_warnings(card, warnings)
    _check_topic_fit(card, warnings, topic_context)

    return _dedupe(warnings)


def _check_required_fields(card: VocabularyCard, warnings: list[str]) -> None:
    if not card.is_valid:
        return
    required = {
        "word/phrase": card.word_or_phrase,
        "target language": card.target_language,
        "part of speech": card.part_of_speech,
        "definition": card.definition,
        "example": card.example,
    }
    for field_name, value in required.items():
        if not str(value or "").strip():
            warnings.append(f"HARD: required field is empty: {field_name}.")


def _check_expected_values(
    card: VocabularyCard,
    warnings: list[str],
    *,
    expected_input: str,
    expected_target_language: str,
    expected_explanation_language: str,
) -> None:
    if expected_input and card.is_valid:
        if _norm(card.word_or_phrase) != _norm(expected_input):
            warnings.append(
                "HARD: input phrase changed: "
                f"expected {expected_input!r}, got {card.word_or_phrase!r}."
            )
    if expected_target_language:
        if _norm(card.target_language) != _norm(expected_target_language):
            warnings.append(
                "HARD: target language mismatch: "
                f"expected {expected_target_language}, got {card.target_language}."
            )
    if expected_explanation_language and _norm(expected_explanation_language) != "no translation":
        if _norm(card.explanation_language) != _norm(expected_explanation_language):
            warnings.append(
                "HARD: explanation language mismatch: "
                f"expected {expected_explanation_language}, got {card.explanation_language}."
            )


def _check_explanation_language_fields(
    card: VocabularyCard,
    warnings: list[str],
    expected_explanation_language: str,
) -> None:
    language = (expected_explanation_language or card.explanation_language or "").strip().casefold()
    values = {label: str(getattr(card, attr, "") or "") for label, attr in TRANSLATION_FIELDS}

    if language == "no translation":
        for label, value in values.items():
            if _strip_sound(value).strip():
                warnings.append(f"HARD: {label} should be empty because 'No translation' is selected.")
        return

    if language not in LANGUAGE_RULES:
        for label, value in values.items():
            if CYRILLIC_RE.search(value):
                warnings.append(f"HARD: Cyrillic characters detected in {label}.")
        return

    rules = LANGUAGE_RULES[language]
    for label, value in values.items():
        plain = _plain(value)
        if not plain.strip():
            warnings.append(f"HARD: {label} is empty for explanation language {expected_explanation_language or card.explanation_language}.")
            continue
        if CYRILLIC_RE.search(plain):
            warnings.append(f"HARD: Cyrillic characters detected in {language.title()} {label}.")
        _check_language_mixing(plain, label, language, rules, warnings)


def _check_language_mixing(
    value: str,
    label: str,
    language: str,
    rules: dict[str, object],
    warnings: list[str],
) -> None:
    lowered = f" {_plain(value).casefold()} "
    words = set(re.findall(r"[a-ząćęłńóśźżáéíóúüñäöüßàèéìíîòóùú]+", lowered, re.IGNORECASE))
    unexpected = words & set(rules.get("unexpected_words", set()))

    # Avoid noisy warnings for short ordinary words unless there are multiple
    # suspicious tokens or strong foreign-language signals.
    if len(unexpected) >= 2:
        warnings.append(
            f"SOFT: possible mixed-language text in {language.title()} {label}: "
            + ", ".join(sorted(unexpected)[:5])
            + "."
        )
    if language != "polish" and POLISH_DIACRITICS_RE.search(value):
        warnings.append(f"HARD: Polish characters detected in {language.title()} {label}.")
    if language == "polish" and SPANISH_DIACRITICS_RE.search(value):
        warnings.append(f"SOFT: Spanish-looking characters detected in Polish {label}.")


def _check_known_bad_patterns(card: VocabularyCard, warnings: list[str]) -> None:
    fields = {
        "word/phrase": card.word_or_phrase,
        "translation/explanation": card.translation_pl,
        "example translation": card.example_pl,
        "grammar note": card.grammar_note,
        "definition": card.definition,
        "example": card.example,
    }
    for field_name, value in fields.items():
        lowered = str(value or "").casefold()
        for pattern, message in KNOWN_QUALITY_PATTERNS:
            if pattern in lowered:
                warnings.append(f"{message} Field: {field_name}.")


def _check_llm_self_warnings(card: VocabularyCard, warnings: list[str]) -> None:
    for warning in card.quality_warnings:
        warning_text = str(warning or "").strip()
        if not warning_text:
            continue
        if warning_text.startswith(("HARD:", "SOFT:")):
            warnings.append(warning_text)
        else:
            warnings.append(f"SOFT: provider self-check: {warning_text}")
    if card.topic_warning.strip():
        warnings.append(f"SOFT: provider topic warning: {card.topic_warning.strip()}")


def _check_topic_fit(card: VocabularyCard, warnings: list[str], topic_context: str) -> None:
    topic = topic_context.strip()
    if not topic:
        return
    if not card.example.strip():
        warnings.append("HARD: topic/context is set, but the example is empty.")
        return

    topic_fit = card.topic_fit.strip().casefold()
    if topic_fit in {"weak", "mismatch", "not_applicable", "not applicable"}:
        warnings.append(f"SOFT: provider marked topic fit as {card.topic_fit!r}.")

    # One intentionally narrow local check for the user's common use case. For
    # arbitrary user topics, the prompt and provider self-check do the semantic
    # work; local code only catches obvious misses.
    topic_l = topic.casefold()
    if any(token in topic_l for token in ("character", "personality", "charakter", "persona", "personalidad")):
        example_l = f" {card.example.casefold()} "
        person_markers = [
            " he ", " she ", " they ", " person ", " people ", " friend ",
            " colleague ", " mother ", " father ", " sister ", " brother ",
            " teacher ", " manager ", " someone", " her ", " his ", " their ",
            " ella ", " él ", " persona ", " gente ", " amigo ", " amiga ",
        ]
        if not any(marker in example_l for marker in person_markers):
            warnings.append(
                "SOFT: topic warning: example may not clearly describe a person's character/personality."
            )


def _plain(value: str) -> str:
    value = re.sub(r"\[sound:[^\]]+\]", " ", value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def _strip_sound(value: str) -> str:
    return re.sub(r"\[sound:[^\]]+\]", "", value or "")


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result
