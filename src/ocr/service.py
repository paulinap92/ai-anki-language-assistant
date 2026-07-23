"""Small local OCR/text-extraction service used by the v9 OCR / Import tab.

This module intentionally keeps OCR optional. Text PDFs and TXT files work with
pure Python fallbacks when available; image OCR requires Pillow + pytesseract and
an installed Tesseract executable on the user's system.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Iterable


class OcrExtractionError(RuntimeError):
    """Raised when OCR/text extraction cannot be completed."""


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTENSIONS = {".txt", ".md"}
HTML_EXTENSIONS = {".html", ".htm"}
PDF_EXTENSIONS = {".pdf"}


def clean_ocr_text(text: str) -> str:
    """Clean common OCR/text-extraction noise without rewriting content."""
    value = (text or "").replace("\ufeff", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    # Keep line breaks, but avoid dozens of empty lines from PDF extraction.
    value = re.sub(r"\n{3,}", "\n\n", value)
    # Remove stray spaces at line boundaries.
    value = "\n".join(line.strip() for line in value.splitlines())
    return value.strip()


def extract_text_from_paths(paths: Iterable[str | Path]) -> str:
    """Extract text from one or more TXT/PDF/image paths and join the results."""
    chunks: list[str] = []
    for path_value in paths:
        path = Path(path_value)
        if not path.exists():
            raise OcrExtractionError(f"File not found: {path}")
        text = extract_text_from_file(path)
        if text.strip():
            chunks.append(f"--- SOURCE: {path.name} ---\n{text.strip()}")
    return clean_ocr_text("\n\n".join(chunks))


def extract_text_from_file(path: str | Path) -> str:
    """Extract text from a supported file path."""
    file_path = Path(path)
    suffix = file_path.suffix.casefold()
    if suffix in TEXT_EXTENSIONS:
        return _extract_text_file(file_path)
    if suffix in HTML_EXTENSIONS:
        return _extract_html_file(file_path)
    if suffix in PDF_EXTENSIONS:
        return _extract_pdf_text(file_path)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image_text(file_path)
    raise OcrExtractionError(
        f"Unsupported file type: {file_path.suffix or '(no extension)'}. "
        "Use TXT, HTML, PDF, PNG, JPG, WEBP, BMP, or TIFF."
    )


def _extract_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            return clean_ocr_text(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    raise OcrExtractionError(f"Could not decode text file: {path.name}")

def _extract_html_file(path: Path) -> str:
    """Extract visible-ish text from a simple HTML lesson/export file."""
    raw_text = _extract_text_file(path)
    # Remove scripts/styles and convert common block boundaries to new lines.
    raw_text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_text)
    raw_text = re.sub(r"(?i)<\s*br\s*/?>", "\n", raw_text)
    raw_text = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6]|section|article|table)\s*>", "\n", raw_text)
    raw_text = re.sub(r"(?s)<[^>]+>", " ", raw_text)
    return clean_ocr_text(html.unescape(raw_text))


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF, OCR-rendering pages only when needed."""
    # Preferred path: PyMuPDF handles text PDFs well and can render scanned pages
    # for local OCR if pytesseract is installed.
    try:
        return _extract_pdf_with_pymupdf(path)
    except ImportError:
        pass
    except Exception as exc:
        raise OcrExtractionError(f"PDF extraction failed for {path.name}: {exc}") from exc

    # Fallback: pypdf/PyPDF2 for simple text PDFs.
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = clean_ocr_text("\n\n".join(pages))
            if text:
                return text
        except ImportError:
            continue
        except Exception as exc:
            raise OcrExtractionError(f"PDF extraction failed for {path.name}: {exc}") from exc

    raise OcrExtractionError(
        "PDF support needs PyMuPDF or pypdf. Install optional OCR dependencies, e.g. "
        "pip install PyMuPDF pypdf pillow pytesseract"
    )


def _extract_pdf_with_pymupdf(path: Path) -> str:
    import fitz  # type: ignore[import-not-found]

    document = fitz.open(str(path))
    text_pages: list[str] = []
    pages_without_text: list[int] = []
    for page_index, page in enumerate(document):
        page_text = page.get_text("text") or ""
        if page_text.strip():
            text_pages.append(page_text)
        else:
            pages_without_text.append(page_index)

    text = clean_ocr_text("\n\n".join(text_pages))
    if text:
        return text

    # Scanned PDF: render pages and run local OCR. Keep the first pass bounded
    # enough for a quick lesson-page test.
    if not pages_without_text:
        pages_without_text = list(range(len(document)))
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrExtractionError(
            "This PDF looks scanned/no-text. Image OCR needs Pillow + pytesseract "
            "and the Tesseract app installed in PATH."
        ) from exc

    ocr_chunks: list[str] = []
    for page_index in pages_without_text[:20]:
        page = document[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        ocr_chunks.append(pytesseract.image_to_string(image))
    return clean_ocr_text("\n\n".join(ocr_chunks))


def _extract_image_text(path: Path) -> str:
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrExtractionError(
            "Image OCR needs optional dependencies: pip install pillow pytesseract. "
            "You also need the Tesseract executable installed and available in PATH."
        ) from exc

    try:
        image = Image.open(path)
        return clean_ocr_text(pytesseract.image_to_string(image))
    except Exception as exc:
        raise OcrExtractionError(f"Image OCR failed for {path.name}: {exc}") from exc
