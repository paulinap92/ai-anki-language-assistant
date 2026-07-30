"""Multimodal import extraction for screenshots/book photos/table images.

This module is intentionally separate from normal card generation. It asks a
vision-capable model to extract structured candidate rows from an image/PDF page
and returns JSON text that the Import Material candidate parser can review.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Iterable

from src.ocr.service import IMAGE_EXTENSIONS, PDF_EXTENSIONS, OcrExtractionError


SUPPORTED_MULTIMODAL_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS


def _clean_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().strip('"').strip("'")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in {"none", "null", "todo"}:
        return None
    if any(marker in lowered for marker in ("your_", "insert_", "paste_", "change_me", "changeme", "placeholder")):
        return None
    return cleaned


def _mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    suffix = path.suffix.casefold()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def _data_url(path: Path) -> str:
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{_mime_type(path)};base64,{encoded}"


def _render_pdf_pages_to_png(path: Path, *, max_pages: int = 5) -> list[Path]:
    """Render the first PDF pages to temporary PNG files for vision models."""
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrExtractionError(
            "PDF multimodal import needs PyMuPDF installed. Install PyMuPDF or use Mistral OCR for PDFs."
        ) from exc

    temp_dir = Path(tempfile.mkdtemp(prefix="ai_anki_multimodal_pdf_"))
    output_paths: list[Path] = []
    try:
        document = fitz.open(str(path))
        for page_index in range(min(len(document), max_pages)):
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            out_path = temp_dir / f"{path.stem}_page_{page_index + 1}.png"
            pixmap.save(str(out_path))
            output_paths.append(out_path)
    except Exception as exc:
        raise OcrExtractionError(f"Could not render PDF for multimodal import: {path.name}: {exc}") from exc
    return output_paths


def _image_paths_for_multimodal(paths: Iterable[str | Path], *, max_pdf_pages: int = 5) -> list[Path]:
    image_paths: list[Path] = []
    for value in paths:
        path = Path(value)
        if not path.exists():
            raise OcrExtractionError(f"File not found: {path}")
        suffix = path.suffix.casefold()
        if suffix in IMAGE_EXTENSIONS:
            image_paths.append(path)
        elif suffix in PDF_EXTENSIONS:
            image_paths.extend(_render_pdf_pages_to_png(path, max_pages=max_pdf_pages))
        else:
            raise OcrExtractionError(
                f"Multimodal import supports image/PDF files only; got {path.name}. Use Local extraction for TXT/HTML."
            )
    if not image_paths:
        raise OcrExtractionError("No image/PDF pages available for multimodal import.")
    return image_paths


def _extract_with_openai(image_paths: list[Path], prompt: str, *, api_key: str | None, model: str | None) -> str:
    resolved_key = api_key or _clean_env_value(os.getenv("OPENAI_API_KEY"))
    if not resolved_key:
        raise OcrExtractionError("OPENAI_API_KEY is missing. Add it to .env before using OpenAI multimodal import.")
    resolved_model = model or _clean_env_value(os.getenv("OPENAI_MULTIMODAL_MODEL")) or _clean_env_value(os.getenv("OPENAI_MODEL")) or "gpt-4.1-mini"
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrExtractionError("OpenAI multimodal import needs the openai package installed.") from exc

    client = OpenAI(api_key=resolved_key)
    content: list[dict[str, object]] = [{"type": "input_text", "text": prompt}]
    for path in image_paths:
        content.append({"type": "input_image", "image_url": _data_url(path)})
    try:
        response = client.responses.create(
            model=resolved_model,
            input=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        raise OcrExtractionError(f"OpenAI multimodal import failed: {exc}") from exc
    return getattr(response, "output_text", "") or ""


def _extract_with_gemini(image_paths: list[Path], prompt: str, *, api_key: str | None, model: str | None) -> str:
    resolved_key = api_key or _clean_env_value(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if not resolved_key:
        raise OcrExtractionError("GEMINI_API_KEY is missing. Add it to .env before using Gemini multimodal import.")
    resolved_model = model or _clean_env_value(os.getenv("GEMINI_MULTIMODAL_MODEL")) or _clean_env_value(os.getenv("GEMINI_MODEL")) or "gemini-2.5-flash"
    try:
        from google import genai  # type: ignore[import-not-found]
        from google.genai import types  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrExtractionError("Gemini multimodal import needs the google-genai package installed.") from exc

    parts: list[object] = [prompt]
    for path in image_paths:
        parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=_mime_type(path)))
    try:
        client = genai.Client(api_key=resolved_key)
        response = client.models.generate_content(model=resolved_model, contents=parts)
    except Exception as exc:
        raise OcrExtractionError(f"Gemini multimodal import failed: {exc}") from exc
    return getattr(response, "text", "") or ""


def extract_candidates_with_multimodal(
    paths: Iterable[str | Path],
    *,
    provider: str,
    prompt: str,
    api_key: str | None = None,
    model: str | None = None,
    max_pdf_pages: int = 5,
) -> str:
    """Extract structured candidate JSON from image/PDF material using a vision model."""
    image_paths = _image_paths_for_multimodal(paths, max_pdf_pages=max_pdf_pages)
    normalized_provider = (provider or "").strip().casefold()
    if "openai" in normalized_provider or "chatgpt" in normalized_provider:
        return _extract_with_openai(image_paths, prompt, api_key=api_key, model=model)
    if "gemini" in normalized_provider or "google" in normalized_provider:
        return _extract_with_gemini(image_paths, prompt, api_key=api_key, model=model)
    raise OcrExtractionError(f"Unsupported multimodal import provider: {provider}")
