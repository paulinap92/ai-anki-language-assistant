from src.domain.languages import LANGUAGE_TAGS, normalize_language


def test_russian_is_supported_learning_language() -> None:
    assert LANGUAGE_TAGS["Russian"] == "russian"
    assert normalize_language("ru") == "Russian"
    assert normalize_language("rosyjski") == "Russian"
    assert normalize_language("русский") == "Russian"


def test_japanese_is_supported_learning_language() -> None:
    assert LANGUAGE_TAGS["Japanese"] == "japanese"
    assert normalize_language("ja") == "Japanese"
    assert normalize_language("japoński") == "Japanese"
    assert normalize_language("日本語") == "Japanese"
