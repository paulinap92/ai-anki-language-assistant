from pathlib import Path


def test_conversation_ui_has_its_own_tutor_voice_selector() -> None:
    text = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    assert 'text="Tutor audio"' in text
    assert '_conversation_tts_voice_var' in text
    assert '_selected_conversation_tts_voice' in text
    assert '_on_conversation_language_changed' in text


def test_flashcard_mode_hides_topic_ui_and_uses_empty_topic_for_ai() -> None:
    text = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    assert '_conversation_topic_frame' in text
    assert 'topic_frame.grid_remove()' in text
    assert 'topic = "" if flashcard_mode else self._topic_var.get().strip()' in text
    assert 'flashcard targets only' in text


def test_voice_lab_has_multilingual_auto_samples() -> None:
    text = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    assert 'TTS_SAMPLE_TEXTS' in text
    assert '"German": "Hallo.' in text
    assert '"French": "Bonjour.' in text
    assert '_sync_speech_preview_text' in text
