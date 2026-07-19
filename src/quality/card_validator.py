"""Local quality validation for generated vocabulary flashcards.

The LLM prompt is useful, but it is not a safety boundary. These checks run
locally after generation and before Anki updates. They intentionally stay
lightweight: they catch obvious language/topic problems and surface warnings for
human review instead of pretending to be a full grammar checker.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from src.domain.models import VocabularyCard


CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
POLISH_DIACRITICS_RE = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
SPANISH_DIACRITICS_RE = re.compile(r"[áéíóúüñ¿¡ÁÉÍÓÚÜÑ]")
# Characters that are strong Spanish-only signals in Polish fields. Note that
# ó is valid Polish, so it must never trigger a Spanish-looking warning.
SPANISH_ONLY_IN_POLISH_RE = re.compile(r"[áéíúüñ¿¡ÁÉÍÚÜÑ]")
GERMAN_DIACRITICS_RE = re.compile(r"[äöüßÄÖÜ]")
ITALIAN_DIACRITICS_RE = re.compile(r"[àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ]")


KNOWN_QUALITY_PATTERNS: list[tuple[str, str]] = [
    ("nostalgja", "HARD: possible typo: 'nostalgja' → 'nostalgia'."),
    ("głęboka smutek", "HARD: possible Polish grammar error: 'głęboka smutek' → 'głęboki smutek'."),
    ("область живота", "HARD: Cyrillic phrase detected: 'область живота'."),
]

UNNATURAL_USAGE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(?:come|comes|came|coming)\s+across\s+(?:some\s+)?(?:rain|snow|wind|heat|weather)\b", re.IGNORECASE),
        "SOFT: example uses 'come across' with weather; this collocation is usually unnatural.",
    ),
    (
        re.compile(r"\bmesmerizing\s+flow\s+of\s+(?:the\s+)?smoothie\b", re.IGNORECASE),
        "HARD: example uses an absurd collocation: 'mesmerizing flow of the smoothie'.",
    ),
    (
        re.compile(r"\bwear\s+down\s+(?:his|her|their|my|your|our)?\s*doubts\b", re.IGNORECASE),
        "SOFT: example uses 'wear down doubts'; 'wear down resistance/patience' is more natural.",
    ),
    (
        re.compile(r"\bzmęczy(?:ć|l|ła|ło|li|ły)?\s+(?:jego|jej|ich|moje|twoje)?\s*wątpliwości\b", re.IGNORECASE),
        "SOFT: translation may be too literal/unnatural: use wording like 'przełamać opór' or 'rozwiać wątpliwości' depending on context.",
    ),
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
GRAMMAR_META_ENGLISH_WORDS = COMMON_ENGLISH_WORDS | {
    "noun", "phrase", "verb", "adjective", "adverb", "article", "articles",
    "preposition", "prepositions", "gerund", "base", "form", "forms",
    "countable", "uncountable", "singular", "plural", "auxiliary",
    "idiom", "idiomatic", "active", "passive", "voice", "tense",
    "collocation", "collocations", "use", "used", "with", "without",
    "normally", "typically", "common", "commonly", "fixed",
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

LEXICAL_STOPWORDS = {
    "a", "an", "the", "to", "of", "and", "or", "but", "with", "for", "from", "in",
    "be", "is", "are", "am", "was", "were", "been", "being", "one", "ones", "someone",
    "something", "somebody", "some", "any", "anyone", "anything", "your", "my", "his", "her",
    "their", "our", "its", "się", "se", "me", "te", "nos", "os", "sich",
}


def validate_vocabulary_card(
    card: VocabularyCard,
    *,
    expected_input: str = "",
    expected_target_language: str = "",
    expected_explanation_language: str = "",
    topic_context: str = "",
) -> list[str]:
    """Return local quality warnings for a generated vocabulary card."""
    warnings: list[str] = []

    _check_required_fields(card, warnings)
    _check_expected_values(
        card,
        warnings,
        expected_input=expected_input,
        expected_target_language=expected_target_language,
        expected_explanation_language=expected_explanation_language,
    )
    _check_example_uses_target_item(card, warnings, expected_input=expected_input)
    _check_explanation_language_fields(card, warnings, expected_explanation_language)
    _check_known_bad_patterns(card, warnings)
    _check_naturalness(card, warnings)
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


def _check_example_uses_target_item(card: VocabularyCard, warnings: list[str], *, expected_input: str) -> None:
    """Ensure the example teaches the requested lexical item, not a synonym/typo.

    This is language-neutral by design. It uses conservative lexical anchors
    instead of a full conjugation engine, so it catches obvious wrong-word cases
    without pretending to understand every morphology of every language.
    """
    if not card.is_valid:
        return
    target = expected_input or card.word_or_phrase
    example = card.example or ""
    if not str(target).strip() or not str(example).strip():
        return

    if card.example_uses_target is False:
        warnings.append("HARD: provider self-check says the example does not use the target item.")

    used_form = str(card.used_form_in_example or "").strip()
    if used_form and _normalize_for_substring(used_form) not in _normalize_for_substring(example):
        warnings.append("SOFT: provider used_form_in_example was not found literally in the example; verify target usage.")

    target_norm = _prepare_lexical_text(target)
    example_norm = _prepare_lexical_text(example)
    target_compact = _normalize_for_substring(target_norm)
    example_compact = _normalize_for_substring(example_norm)
    if target_compact and target_compact in example_compact:
        return

    anchors = _target_anchors(target)
    if not anchors:
        return
    example_tokens = _tokens_for_matching(example)
    hits = [anchor for anchor in anchors if _anchor_hits_example(anchor, example_tokens, example_norm)]

    if not hits:
        warnings.append(
            "HARD: example does not use the target word/phrase or a valid-looking inflected form; "
            "do not replace the target with a synonym, typo, or visually similar word."
        )
        return

    # Multi-word expressions can be discontinuous or inflected. If only one of
    # several anchors is present, surface a soft warning for review rather than
    # blocking automatically.
    if len(anchors) >= 2 and len(hits) < min(2, len(anchors)):
        warnings.append(
            "SOFT: example only partially matches the target phrase; check that it teaches the requested expression."
        )


def _target_anchors(target: str) -> list[str]:
    text = _prepare_lexical_text(target)
    # Optional reflexive/pronominal marker in input, e.g. derrumbar(se), should
    # not become the only anchor.
    text = re.sub(r"\((?:se|sich|się|oneself)\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[/](?:se|sich|się)\b", " ", text, flags=re.IGNORECASE)
    text = _remove_outer_to(text)
    tokens = _tokens_for_matching(text)
    anchors: list[str] = []
    for token in tokens:
        if token in LEXICAL_STOPWORDS or len(token) < 3:
            continue
        variants = {token, _light_stem(token)}
        if token.endswith("se") and len(token) > 5:
            base = token[:-2]
            variants.add(base)
            variants.add(_light_stem(base))
        for variant in variants:
            if variant and len(variant) >= 3 and variant not in LEXICAL_STOPWORDS:
                anchors.append(variant)
    return _dedupe(anchors)


def _anchor_hits_example(anchor: str, example_tokens: list[str], example_norm: str) -> bool:
    if anchor in example_tokens:
        return True
    if len(anchor) >= 5 and any(token.startswith(anchor) or anchor.startswith(token) for token in example_tokens if len(token) >= 4):
        return True
    if len(anchor) >= 5 and re.search(rf"\b{re.escape(anchor)}[a-z]*\b", example_norm):
        return True
    return False


def _light_stem(token: str) -> str:
    """Return a conservative cross-language stem for lexical anchoring."""
    token = _normalize_letters(token)
    suffixes = (
        "mente", "amiento", "imiento", "aciones", "zione", "zioni", "ungen",
        "ando", "iendo", "ized", "ised", "ing", "ed", "es", "s",
        "ar", "er", "ir", "re", "en", "n",
    )
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _tokens_for_matching(value: str) -> list[str]:
    text = _normalize_letters(value)
    return re.findall(r"[a-ząćęłńóśźż]+", text, flags=re.IGNORECASE)


def _prepare_lexical_text(value: str) -> str:
    text = _strip_outer_quotes(str(value or "").strip())
    text = text.replace("…", "...")
    return _normalize_letters(text.casefold())


def _normalize_letters(value: str) -> str:
    text = str(value or "")
    replacements = {"ł": "l", "Ł": "l", "ß": "ss", "æ": "ae", "œ": "oe"}
    text = "".join(replacements.get(char, char) for char in text)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _remove_outer_to(value: str) -> str:
    return re.sub(r"^to\s+", "", str(value or "").strip(), flags=re.IGNORECASE)


def _normalize_for_substring(value: str) -> str:
    return re.sub(r"[^a-z0-9ąćęłńóśźż]+", " ", _normalize_letters(value)).strip()


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
    plain = _plain(value)
    if language == "polish":
        # Do not warn about Spanish-specific characters in Polish explanation fields.
        # In language-learning cards, Polish grammar notes/translations often quote
        # target-language words, especially when target_language is Spanish. Cyrillic
        # is still handled as a HARD warning above.
        pass
    elif POLISH_DIACRITICS_RE.search(plain):
        warnings.append(f"HARD: Polish characters detected in {language.title()} {label}.")

    if label == "grammar note":
        return

    cleaned = _remove_quoted_fragments(plain.casefold())
    words = set(re.findall(r"[a-ząćęłńóśźżáéíóúüñäöüßàèéìíîòóùú]+", cleaned, re.IGNORECASE))
    unexpected = words & set(rules.get("unexpected_words", set()))
    if language == "polish":
        unexpected -= GRAMMAR_META_ENGLISH_WORDS
    content_like = {word for word in unexpected if len(word) > 3}
    if len(content_like) >= 4:
        warnings.append(
            f"SOFT: possible mixed-language text in {language.title()} {label}: "
            + ", ".join(sorted(content_like)[:5])
            + "."
        )


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


def _check_naturalness(card: VocabularyCard, warnings: list[str]) -> None:
    combined = "\n".join([
        str(card.example or ""),
        str(card.example_pl or ""),
        str(card.translation_pl or ""),
        str(card.grammar_note or ""),
    ])
    for pattern, message in UNNATURAL_USAGE_PATTERNS:
        if pattern.search(combined):
            warnings.append(message)

    collocation = str(card.collocation_naturalness or "").strip().casefold()
    if collocation == "weak":
        warnings.append("SOFT: provider self-check marked collocation naturalness as weak.")
    elif collocation == "bad":
        warnings.append("HARD: provider self-check marked collocation naturalness as bad.")

    translation = str(card.translation_naturalness or "").strip().casefold()
    if translation == "weak":
        warnings.append("SOFT: provider self-check marked translation naturalness as weak.")
    elif translation == "bad":
        warnings.append("HARD: provider self-check marked translation naturalness as bad.")


def _check_llm_self_warnings(card: VocabularyCard, warnings: list[str]) -> None:
    for warning in card.quality_warnings:
        warning_text = str(warning or "").strip()
        if not warning_text:
            continue
        if _is_noisy_provider_warning(warning_text):
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


def normalize_lexical_value(value: str) -> str:
    """Normalize user/provider lexical values for exact-input comparisons.

    This intentionally strips only outer quotation marks. Quoted phrases such as
    ``"Nevertheless…"`` and ``Nevertheless…`` are the same learning item;
    internal apostrophes remain meaningful.
    """
    text = " ".join(str(value or "").strip().split())
    text = _strip_outer_quotes(text)
    text = text.replace("…", "...")
    return text.casefold()


def _norm(value: str) -> str:
    return normalize_lexical_value(value)


def _strip_outer_quotes(value: str) -> str:
    text = str(value or "").strip()
    quote_pairs = (("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’"))
    changed = True
    while changed and len(text) >= 2:
        changed = False
        for left, right in quote_pairs:
            if text.startswith(left) and text.endswith(right):
                text = text[1:-1].strip()
                changed = True
                break
    return text


def _remove_quoted_fragments(value: str) -> str:
    text = re.sub(r"'[^']*'", " ", value)
    text = re.sub(r'"[^"]*"', " ", text)
    text = re.sub(r"‘[^’]*’", " ", text)
    text = re.sub(r"“[^”]*”", " ", text)
    return text


def _is_noisy_provider_warning(warning_text: str) -> bool:
    lowered = warning_text.casefold()
    if "spanish-looking characters detected in polish" in lowered:
        return True
    if "possible mixed-language text in polish grammar note" in lowered:
        return True
    return False


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result
