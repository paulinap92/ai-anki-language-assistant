import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ui.modern_gui import ModernVocabularyGui


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _gui() -> ModernVocabularyGui:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._speech_audio_status_by_note_id = {}
    gui._speech_audio_error_by_note_id = {}
    gui._speech_source_field_var = _Var("Auto: Example/ContextExample/Back/Word")
    gui._speech_target_field_var = _Var("Audio")
    gui._speech_write_mode_var = _Var("Use dedicated audio field")
    return gui


def test_audio_coverage_counts_full_scan_not_only_missing_rows() -> None:
    gui = _gui()
    notes = [
        {
            "note_id": 1,
            "model": "AI Vocabulary Light Card",
            "word": "ready",
            "example": "This sentence is ready for audio.",
            "audio_status": "missing_audio",
            "fields": {
                "Word": "ready",
                "Example": "This sentence is ready for audio.",
                "Audio": "",
            },
        },
        {
            "note_id": 2,
            "model": "AI Vocabulary Light Card",
            "word": "done",
            "example": "This one already has audio.",
            "audio_status": "has_audio",
            "fields": {
                "Word": "done",
                "Example": "This one already has audio.",
                "Audio": "[sound:done.mp3]",
            },
        },
        {
            "note_id": 3,
            "model": "Basic",
            "word": "legacy",
            "example": "Legacy note without a dedicated audio field.",
            "audio_status": "missing_audio_field",
            "fields": {
                "Front": "legacy",
                "Back": "Legacy note without a dedicated audio field.",
            },
        },
    ]
    gui._speech_audio_status_by_note_id = {
        int(note["note_id"]): str(note["audio_status"]) for note in notes
    }

    summary = gui._speech_scan_summary(notes)

    assert "1/3 (33.3%) have audio" in summary
    assert "2 need attention" in summary
    assert "1 ready to generate" in summary
    assert "1 need a target audio field" in summary
