# v9.0 OCR / Import foundation

This is the first OCR/import milestone. It intentionally adds only the minimum safe workflow for one practical trial.

## Added

- New `OCR / Import` tab.
- Load TXT, PDF, one image, or multiple images.
- Run text extraction / local OCR into an editable preview textbox.
- Clean extracted text.
- Extract Batch-ready candidates with the selected Card AI provider.
- Editable candidate rows.
- Send candidate rows to Batch without adding directly to Anki.

## Candidate modes

- `Provided examples`: produces `target | source sentence` style rows for Batch `Provided examples`.
- `Vocabulary`: produces word/phrase rows for Batch `Vocabulary`.
- `Grammar`: produces grammar/structure rows for Batch `Grammar`.
- `Mixed`: experimental; rows keep per-candidate type when sent to Batch.

## Important safety decision

OCR/import is not allowed to do:

```text
image/PDF → Anki
```

It only does:

```text
image/PDF → OCR/text preview → candidates → Batch → review → Anki
```

This keeps duplicate handling and manual review in the existing Batch workflow.

## Optional dependencies

Python packages for better OCR/PDF support:

```bash
pip install PyMuPDF pypdf pillow pytesseract
```

Image OCR also requires the Tesseract executable installed on the system and available in PATH.

## Tested

```bash
python -m compileall -q src tests
pytest -q tests/ai/test_prompt_quality_validation.py tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompts_topics.py tests/anki tests/speech
```

Result: 43 passed.
