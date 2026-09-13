from pathlib import Path


MODERN_GUI = Path(__file__).resolve().parents[2] / "src" / "ui" / "modern_gui.py"


def test_new_import_search_resets_previous_review_state() -> None:
    text = MODERN_GUI.read_text(encoding="utf-8")

    assert "self._ocr_ai_search_serial += 1" in text
    assert 'self._ocr_review_priority_filter_var.set("All priorities")' in text
    assert 'self._ocr_review_type_filter_var.set("All types")' in text
    assert 'self._ocr_review_search_var.set("")' in text
    assert "self._set_ocr_candidate_items([])" in text


def test_delayed_retry_cannot_overwrite_a_newer_import_search() -> None:
    text = MODERN_GUI.read_text(encoding="utf-8")

    assert "Ignoring stale Import Material retry" in text
    assert "Discarding stale Import Material result before render" in text
    assert "run_id=rid" in text
    assert "run_settings=settings" in text


def test_import_search_logs_raw_parsed_and_deduped_counts() -> None:
    text = MODERN_GUI.read_text(encoding="utf-8")

    assert "raw_candidates=%s" in text
    assert "parsed_candidates=%s" in text
    assert "raw_merged=%s deduped=%s" in text
