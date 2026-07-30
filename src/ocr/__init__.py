"""OCR / Import helpers for extracting lesson text before Batch generation."""

from src.ocr.service import HTML_EXTENSIONS, TEXT_EXTENSIONS, OcrExtractionError, clean_ocr_text, extract_text_from_paths
from src.ocr.mistral_service import extract_text_with_mistral
from src.ocr.multimodal_service import extract_candidates_with_multimodal

__all__ = [
    "HTML_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "OcrExtractionError",
    "clean_ocr_text",
    "extract_text_from_paths",
    "extract_text_with_mistral",
    "extract_candidates_with_multimodal",
]
