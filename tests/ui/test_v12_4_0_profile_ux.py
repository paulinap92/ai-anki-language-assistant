import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.core.learning_profile import LearningProfile
from src.ui.modern_gui import ModernVocabularyGui


def _write_piper_voice(tmp_path: Path, name: str, language: str, code: str) -> Path:
    model = tmp_path / f"{name}.onnx"
    model.write_bytes(b"fake")
    config = model.with_name(model.name + ".json")
    config.write_text(
        json.dumps(
            {
                "language": {"name_english": language, "code": code, "family": code[:2]},
                "dataset": name,
                "audio": {"quality": "medium"},
            }
        ),
        encoding="utf-8",
    )
    return model


def test_piper_voice_list_is_strictly_filtered_by_profile_language(tmp_path: Path) -> None:
    spanish = _write_piper_voice(tmp_path, "spanish_voice", "Spanish", "es_ES")
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._speech_service = SimpleNamespace(
        providers={
            "Piper Local": SimpleNamespace(
                voices=[str(spanish)],
                models=[str(spanish)],
                default_model=str(spanish),
                default_voice=str(spanish),
            )
        }
    )
    gui._runtime_voice_values = {}
    gui._runtime_voice_languages = {}

    assert gui._voice_options_for_provider("Piper Local", "Spanish")
    assert gui._voice_options_for_provider("Piper Local", "English") == []


def test_multilingual_cloud_voice_matches_any_learning_language() -> None:
    assert ModernVocabularyGui._voice_language_matches("Multilingual", "Spanish")
    assert ModernVocabularyGui._voice_language_matches("Multilingual", "English")


def test_apply_profile_updates_all_language_state(monkeypatch) -> None:
    class Var:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value
        def get(self):
            return self.value

    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    for name in (
        "_language_var",
        "_speech_language_var",
        "_conversation_language_var",
        "_voice_library_language_var",
        "_explanation_language_var",
        "_feedback_language_var",
        "_improvement_level_var",
        "_profile_summary_var",
        "_profile_language_var",
        "_profile_level_var",
        "_profile_support_language_var",
    ):
        setattr(gui, name, Var())

    profile = LearningProfile("Spanish", "Strong B2/C1", "Polish")
    gui._apply_learning_profile(profile, refresh_widgets=False)

    assert gui._language_var.get() == "Spanish"
    assert gui._speech_language_var.get() == "Spanish"
    assert gui._conversation_language_var.get() == "Spanish"
    assert gui._voice_library_language_var.get() == "Spanish"
    assert gui._explanation_language_var.get() == "Polish"
    assert gui._feedback_language_var.get() == "Polish"
    assert gui._improvement_level_var.get() == "Strong B2/C1"


def test_russian_and_japanese_are_profile_and_stt_languages() -> None:
    from src.domain.languages import LANGUAGE_TAGS
    from src.ui.modern_gui import STT_LANGUAGE_CODES, TTS_SAMPLE_TEXTS

    assert "Russian" in LANGUAGE_TAGS
    assert "Japanese" in LANGUAGE_TAGS
    assert STT_LANGUAGE_CODES["Russian"] == "ru"
    assert STT_LANGUAGE_CODES["Japanese"] == "ja"
    assert TTS_SAMPLE_TEXTS["Russian"]
    assert TTS_SAMPLE_TEXTS["Japanese"]
