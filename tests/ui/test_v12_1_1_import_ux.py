import sys
import types

sys.modules.setdefault("customtkinter", types.ModuleType("customtkinter"))

from src.ui.modern_gui import (
    ModernVocabularyGui,
    OCR_EXTRACTION_MODES,
    OCR_EXTRACTION_MODE_HELP,
)


def test_import_ui_exposes_only_four_product_modes() -> None:
    assert OCR_EXTRACTION_MODES == [
        "Vocabulary & expressions",
        "Grammar",
        "Examples / sentences",
        "Auto",
    ]


def test_import_product_modes_map_to_existing_internal_contracts() -> None:
    assert ModernVocabularyGui._ocr_internal_mode("Vocabulary & expressions") == "Vocabulary + source examples"
    assert ModernVocabularyGui._ocr_internal_mode("Grammar") == "Smart grammar import"
    assert ModernVocabularyGui._ocr_internal_mode("Examples / sentences") == "Provided examples"
    assert ModernVocabularyGui._ocr_internal_mode("Auto") == "Mixed"


def test_import_mode_help_is_present_for_every_visible_mode() -> None:
    assert set(OCR_EXTRACTION_MODES) == set(OCR_EXTRACTION_MODE_HELP)
    assert "whole source" in OCR_EXTRACTION_MODE_HELP["Vocabulary & expressions"]
    assert "structures" in OCR_EXTRACTION_MODE_HELP["Grammar"]
    assert "exact source-sentence" in OCR_EXTRACTION_MODE_HELP["Examples / sentences"]
    assert "classify" in OCR_EXTRACTION_MODE_HELP["Auto"]
