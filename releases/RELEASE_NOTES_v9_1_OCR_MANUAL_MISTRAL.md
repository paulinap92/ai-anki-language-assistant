# v9.1 OCR manual picker + Mistral auto candidates

## Added

- OCR / Import now has two explicit workflows:
  - `Tesseract/local OCR + manual picker`
  - `Mistral OCR auto candidates`
- Manual picker buttons:
  - `Use selection as target`
  - `Add target | sentence`
  - `Add vocabulary`
  - `Add grammar`
- Mistral OCR provider:
  - Uses `MISTRAL_API_KEY` and `MISTRAL_OCR_MODEL` from `.env`.
  - Supports local PDF/image files through base64 data URLs.
  - Returns extracted markdown/text to the preview area.
  - Then automatically runs the existing Card AI candidate extraction step.
- Updated OCR documentation and `.env.example`.
- Added `mistralai` to `requirements.txt`.

## Not changed

- OCR still does not add anything directly to Anki.
- Duplicate handling remains in Batch.
- Mistral OCR is not an audio provider.
