from pathlib import Path

from src.core.learning_profile import LearningProfile, load_learning_profile, save_learning_profile


def test_learning_profile_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "user_profile.json"
    profile = LearningProfile("Spanish", "Strong B2/C1", "Polish")
    save_learning_profile(profile, path)

    loaded = load_learning_profile(path)

    assert loaded == profile
    assert loaded is not None
    assert loaded.summary == "Spanish · Strong B2/C1 · Polish support"


def test_incomplete_profile_is_not_loaded(tmp_path: Path) -> None:
    path = tmp_path / "user_profile.json"
    path.write_text('{"learning_language":"Spanish","level":"","support_language":"Polish"}', encoding="utf-8")

    assert load_learning_profile(path) is None
