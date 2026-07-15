from pathlib import Path

from src.speech.cache import AudioCache
from src.speech.models import TtsRequest


def test_cache_key_changes_with_voice(tmp_path: Path) -> None:
    cache = AudioCache(tmp_path)
    first = cache.path_for("Provider", TtsRequest("Hello", "English", "m", "a"), "mp3")
    second = cache.path_for("Provider", TtsRequest("Hello", "English", "m", "b"), "mp3")
    assert first != second


def test_cache_key_is_stable_for_equivalent_whitespace(tmp_path: Path) -> None:
    cache = AudioCache(tmp_path)
    first = cache.path_for("Provider", TtsRequest("Hello   world", "English", "m", "a"), "mp3")
    second = cache.path_for("Provider", TtsRequest("Hello world", "English", "m", "a"), "mp3")
    assert first == second
