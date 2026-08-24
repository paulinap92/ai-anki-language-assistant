from pathlib import Path


def _gui_text() -> str:
    return Path("src/ui/modern_gui.py").read_text(encoding="utf-8")


def test_public_tabs_use_queue_and_no_slash_names() -> None:
    text = _gui_text()
    assert '"Queue"' in text
    assert '"Speech & Audio"' in text
    assert '"Advanced"' in text
    assert '"Conversation"' in text
    assert '"Batch"' not in text
    assert '"Speech / Audio"' not in text
    assert '"Advanced / LLMOps"' not in text


def test_conversation_mode_is_chosen_before_mode_specific_controls() -> None:
    text = _gui_text()
    assert 'text="Practice with"' in text
    assert 'text="Start conversation"' in text
    assert '_conversation_topic_frame' in text
    assert '_conversation_flashcard_settings_frame' in text
    assert 'topic_frame.grid_remove()' in text
    assert 'flashcard_frame.grid_remove()' in text
    assert 'text="Start from flashcards"' not in text


def test_flashcard_mode_still_drops_topic_from_ai_context() -> None:
    text = _gui_text()
    assert 'topic = "" if flashcard_mode else self._topic_var.get().strip()' in text
    assert 'flashcard targets only' in text


def test_import_txt_html_is_presented_as_local_read_not_ai_extraction() -> None:
    text = _gui_text()
    assert 'TXT/HTML are simply read on your computer — no model or API is used.' in text
    assert 'text="Read material locally"' in text
    assert 'method_label.grid_remove()' in text
    assert 'method_box.grid_remove()' in text
    assert 'text="Find candidates with AI"' in text


def test_queue_progress_is_human_readable_and_hides_zero_noise() -> None:
    text = _gui_text()
    assert 'f"Prepared {prepared} of {total}"' in text
    assert 'f"{waiting} waiting"' in text
    assert '_batch_progress_bar' in text
    assert 'Added {added_total}' in text
    assert 'Rate limited {counts' in text
    assert 'Remaining {remaining}' not in text
