"""Optional Mistral OCR provider for the OCR / Import tab.

This module is intentionally optional: the app still runs without the
``mistralai`` package or without ``MISTRAL_API_KEY``. Mistral OCR is used only
when the user explicitly clicks the Mistral OCR / Auto button in the UI.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Iterable

from src.ocr.service import IMAGE_EXTENSIONS, PDF_EXTENSIONS, OcrExtractionError, clean_ocr_text


MISTRAL_SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS


_MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _create_mistral_client(api_key: str):
    """Create a Mistral client while tolerating SDK import-path changes."""
    try:
        from mistralai.client import Mistral  # type: ignore[import-not-found]
    except ImportError:
        try:
            from mistralai import Mistral  # type: ignore[import-not-found,no-redef]
        except ImportError as exc:
            raise OcrExtractionError(
                "Mistral OCR needs the optional Python package: pip install mistralai"
            ) from exc
    return Mistral(api_key=api_key)


def _data_url_for_file(path: Path) -> str:
    suffix = path.suffix.casefold()
    mime = _MIME_BY_EXTENSION.get(suffix)
    if not mime:
        raise OcrExtractionError(
            f"Mistral OCR supports PDF/images only in this app; got {path.suffix or '(no extension)'}"
        )
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _response_pages_markdown(response: object) -> str:
    """Return combined markdown/text from a Mistral OCR response object."""
    pages = getattr(response, "pages", None)
    if pages is None and isinstance(response, dict):
        pages = response.get("pages")
    chunks: list[str] = []
    if pages:
        for page in pages:
            markdown = getattr(page, "markdown", None)
            if markdown is None and isinstance(page, dict):
                markdown = page.get("markdown")
            if markdown:
                chunks.append(str(markdown))
    if chunks:
        return clean_ocr_text("\n\n".join(chunks))

    # Last resort: SDK objects normally support model_dump_json, but we avoid
    # importing pydantic here and keep the app alive with a readable diagnostic.
    dumped = getattr(response, "model_dump_json", None)
    if callable(dumped):
        return clean_ocr_text(str(dumped()))
    return clean_ocr_text(str(response))


def extract_text_with_mistral(paths: Iterable[str | Path], *, api_key: str | None = None, model: str | None = None) -> str:
    """Run Mistral OCR on PDF/image files and return combined markdown text.

    Args:
        paths: One or more local PDF/image paths.
        api_key: Optional explicit API key; defaults to ``MISTRAL_API_KEY``.
        model: Optional OCR model; defaults to ``MISTRAL_OCR_MODEL`` or
            ``mistral-ocr-latest``.
    """
    resolved_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not resolved_key:
        raise OcrExtractionError(
            "MISTRAL_API_KEY is missing. Add it to .env before using Mistral OCR."
        )
    resolved_model = model or os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
    client = _create_mistral_client(resolved_key)

    chunks: list[str] = []
    for path_value in paths:
        path = Path(path_value)
        if not path.exists():
            raise OcrExtractionError(f"File not found: {path}")
        suffix = path.suffix.casefold()
        if suffix not in MISTRAL_SUPPORTED_EXTENSIONS:
            raise OcrExtractionError(
                f"Mistral OCR supports PDF/images only in this app; got {path.name}"
            )
        document_type = "document_url" if suffix in PDF_EXTENSIONS else "image_url"
        document_key = "document_url" if document_type == "document_url" else "image_url"
        try:
            response = client.ocr.process(
                model=resolved_model,
                document={
                    "type": document_type,
                    document_key: _data_url_for_file(path),
                },
                table_format="markdown",
                include_image_base64=False,
            )
        except Exception as exc:
            raise OcrExtractionError(f"Mistral OCR failed for {path.name}: {exc}") from exc
        text = _response_pages_markdown(response)
        if text.strip():
            chunks.append(f"--- SOURCE: {path.name} ---\n{text.strip()}")
    return clean_ocr_text("\n\n".join(chunks))
