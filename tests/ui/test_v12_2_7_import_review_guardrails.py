from __future__ import annotations

import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ui.modern_gui import IMPORT_REVIEW_PAGE_SIZE, ModernVocabularyGui


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _review_gui(items: list[dict[str, str]]) -> ModernVocabularyGui:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._ocr_candidate_items = items
    gui._ocr_candidate_vars = [_Var(False) for _ in items]
    gui._ocr_review_priority_filter_var = _Var("All priorities")
    gui._ocr_review_type_filter_var = _Var("All types")
    gui._ocr_review_search_var = _Var("")
    gui._ocr_review_page = 0
    gui._ocr_candidate_status_var = _Var("")
    return gui


def test_source_size_guardrails_apply_to_source_not_candidate_count() -> None:
    normal = "word " * 1000
    soft = "word " * 12000
    hard = "word " * 32000

    assert ModernVocabularyGui._import_source_size_level(normal) == "normal"
    assert ModernVocabularyGui._import_source_size_level(soft) == "soft"
    assert ModernVocabularyGui._import_source_size_level(hard) == "hard"

    soft_summary = ModernVocabularyGui._import_material_size_summary(soft)
    hard_summary = ModernVocabularyGui._import_material_size_summary(hard)
    assert "Large source" in soft_summary
    assert "chapter/section" in soft_summary
    assert "full-source AI search is blocked" in hard_summary
    assert "No fixed candidate count" in hard_summary


def test_review_priority_uses_existing_metadata_without_fixed_quota() -> None:
    assert ModernVocabularyGui._candidate_review_priority(
        {
            "type": "vocabulary",
            "target": "a bottleneck",
            "candidate_kind": "collocation",
            "source_section": "reading_text",
        }
    ) == "Recommended"

    assert ModernVocabularyGui._candidate_review_priority(
        {
            "type": "vocabulary",
            "target": "systemic problems",
            "source_section": "reading_text",
        }
    ) == "Useful"

    assert ModernVocabularyGui._candidate_review_priority(
        {
            "type": "vocabulary",
            "target": "The Phoebus Cartel",
            "source_section": "reading_text",
        }
    ) == "Optional"


def test_review_filters_and_pagination_do_not_drop_candidates() -> None:
    items = []
    for i in range(60):
        items.append(
            {
                "type": "vocabulary",
                "target": f"phrase {i}",
                "candidate_kind": "collocation" if i < 30 else "word",
                "source_section": "reading_text",
            }
        )
    gui = _review_gui(items)

    assert len(gui._ocr_filtered_candidate_indices()) == 60
    assert len(gui._ocr_visible_candidate_indices()) == IMPORT_REVIEW_PAGE_SIZE

    gui._ocr_review_priority_filter_var.set("Recommended")
    filtered = gui._ocr_filtered_candidate_indices()
    assert len(filtered) == 30
    assert len(gui._ocr_visible_candidate_indices()) == IMPORT_REVIEW_PAGE_SIZE

    gui._ocr_review_page = 1
    assert len(gui._ocr_visible_candidate_indices()) == 5


def test_select_recommended_selects_only_recommended_items() -> None:
    items = [
        {"type": "vocabulary", "target": "a bottleneck", "candidate_kind": "collocation"},
        {"type": "vocabulary", "target": "systemic problems"},
        {"type": "vocabulary", "target": "The Phoebus Cartel"},
    ]
    gui = _review_gui(items)

    gui._select_recommended_ocr_candidates()

    assert [var.get() for var in gui._ocr_candidate_vars] == [True, False, False]
    assert "1 Recommended" in gui._ocr_candidate_status_var.get()
