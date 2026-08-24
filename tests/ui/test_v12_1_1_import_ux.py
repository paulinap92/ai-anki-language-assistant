import sys
import types

sys.modules.setdefault("customtkinter", types.ModuleType("customtkinter"))

from src.ui.modern_gui import ModernVocabularyGui, OCR_EXTRACTION_MODES, OCR_EXTRACTION_MODE_HELP


def test_import_ui_restores_original_mature_modes() -> None:
    assert OCR_EXTRACTION_MODES == [
        "Provided examples",
        "Vocabulary",
        "Vocabulary + source examples",
        "Smart vocabulary",
        "Grammar",
        "Smart grammar import",
        "Mixed",
    ]


def test_original_modes_keep_their_own_internal_contracts() -> None:
    for mode in OCR_EXTRACTION_MODES:
        assert ModernVocabularyGui._ocr_internal_mode(mode) == mode


def test_short_lived_simplified_labels_remain_compatible() -> None:
    assert ModernVocabularyGui._ocr_internal_mode("Vocabulary & expressions") == "Vocabulary + source examples"
    assert ModernVocabularyGui._ocr_internal_mode("Examples / sentences") == "Provided examples"
    assert ModernVocabularyGui._ocr_internal_mode("Auto") == "Mixed"


def test_help_exists_for_all_restored_modes() -> None:
    assert set(OCR_EXTRACTION_MODES).issubset(OCR_EXTRACTION_MODE_HELP)
    assert "selective" in OCR_EXTRACTION_MODE_HELP["Smart vocabulary"].lower()
