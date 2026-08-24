from src.ui.modern_gui import OCR_EXTRACTION_MODES, ModernVocabularyGui


def test_smart_vocabulary_is_visible_in_restored_mode_set():
    assert "Smart vocabulary" in OCR_EXTRACTION_MODES


def test_smart_vocabulary_routes_to_original_smart_contract():
    assert ModernVocabularyGui._ocr_internal_mode("Smart vocabulary") == "Smart vocabulary"


def test_grammar_and_smart_grammar_are_separate_again():
    assert ModernVocabularyGui._ocr_internal_mode("Grammar") == "Grammar"
    assert ModernVocabularyGui._ocr_internal_mode("Smart grammar import") == "Smart grammar import"


def test_mixed_is_visible_again():
    assert "Mixed" in OCR_EXTRACTION_MODES
