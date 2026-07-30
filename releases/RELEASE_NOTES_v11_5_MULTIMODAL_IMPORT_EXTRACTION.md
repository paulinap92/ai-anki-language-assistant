# v11.5 — Multimodal Import Extraction

This release adds a first multimodal Import Material workflow for screenshots, textbook tables and book-photo imports.

## Added

- Added Import Material methods:
  - `OpenAI multimodal import`
  - `Gemini multimodal import`
- Added `src/ocr/multimodal_service.py` for image/PDF-page multimodal extraction.
- Added multimodal prompt builder for table-aware candidate extraction.
- Multimodal extraction asks the model to read the visual layout directly instead of relying only on OCR text.
- For discourse/grammar tables, the expected mapping is:
  - `Expression` → grammar target
  - `Example` → sentence/audio
  - `Use` → source rule / note
- Slash alternatives such as `Actually / Incidentally` must be preserved instead of silently choosing only one option.
- Highlighted/underlined/circled book-photo items can be extracted as candidate drafts with source sentences when visible.
- Multimodal import writes a readable structured summary into Reviewed source text and candidate drafts into Candidate drafts / cherry-pick.
- PDF files are rendered to image pages for multimodal import when PyMuPDF is available.
- Added optional `.env` settings:
  - `OPENAI_MULTIMODAL_MODEL`
  - `GEMINI_MULTIMODAL_MODEL`

## Not changed

- Multimodal import still does not add anything directly to Anki.
- Candidate review and Batch / Queue remain required.
- Mistral OCR remains available for text/markdown extraction.
- Card AI provider, Audio provider and Conversation model remain separate concerns.
- No RAG, LangGraph or cloud agent is added in this version.

## Validation

- `python -m py_compile src/ocr/multimodal_service.py src/ocr/__init__.py src/ui/modern_gui.py src/ai/prompts.py`
- `python -m compileall -q src main_gui_custom.py main_gui_custom_private.py`
