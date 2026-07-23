"""Supported language options for the vocabulary generator."""

SUPPORTED_LANGUAGES = {
    "1": "English",
    "2": "Spanish",
    "3": "German",
    "4": "French",
    "5": "Italian",
    "6": "Portuguese",
}

LANGUAGE_TAGS = {
    "English": "english",
    "Spanish": "spanish",
    "German": "german",
    "French": "french",
    "Italian": "italian",
    "Portuguese": "portuguese",
}


def normalize_language(language: str) -> str:
    """Normalize and validate a supported language name.

    Args:
        language: Language selected or configured by the user.

    Returns:
        Normalized supported language name.

    Raises:
        ValueError: If the provided language is not supported.
    """
    cleaned = language.strip().lower()

    aliases = {
        "en": "English",
        "eng": "English",
        "english": "English",
        "angielski": "English",
        "es": "Spanish",
        "esp": "Spanish",
        "spanish": "Spanish",
        "espanol": "Spanish",
        "español": "Spanish",
        "hiszpanski": "Spanish",
        "hiszpański": "Spanish",
        "de": "German",
        "deutsch": "German",
        "german": "German",
        "niemiecki": "German",
        "fr": "French",
        "french": "French",
        "francais": "French",
        "français": "French",
        "francuski": "French",
        "it": "Italian",
        "italian": "Italian",
        "italiano": "Italian",
        "wloski": "Italian",
        "włoski": "Italian",
        "pt": "Portuguese",
        "portuguese": "Portuguese",
        "portugues": "Portuguese",
        "português": "Portuguese",
        "portugalski": "Portuguese",
    }

    if cleaned not in aliases:
        supported = ", ".join(LANGUAGE_TAGS)
        raise ValueError(
            f"Unsupported language: {language}. Supported languages: {supported}."
        )

    return aliases[cleaned]


def get_language_tag(language: str) -> str:
    """Return an Anki-friendly language tag.

    Args:
        language: Normalized language name.

    Returns:
        Lowercase tag without spaces.
    """
    return LANGUAGE_TAGS.get(language, language.lower().replace(" ", "_"))
