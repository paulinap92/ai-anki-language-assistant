# v9.1.1 – Import Material flow fix

Fixes the first OCR / Import MVP flow problems discovered during testing.

## Fixed

- Renamed the tab from `OCR / Import` to `Import Material`.
- The import method dropdown now controls the actual pipeline.
- Selecting `Mistral OCR auto candidates` no longer calls local Tesseract.
- The main import button now changes label depending on the selected method:
  - `Extract text locally`
  - `Run Mistral extraction`
- Removed the confusing separate `Mistral OCR + auto candidates` button from the main flow.
- Renamed confusing manual picker buttons:
  - `Use selection as target` → `Save selected target`
  - `Add target | sentence` → `Add target + example`
- Added visible candidate-basket actions under the basket:
  - `Send selected to Batch / Queue`
  - `Clear basket`
- Candidate rows are now displayed in readable form instead of raw TSV/provider fields:
  - `provided example | target | source sentence`
  - `provided example | source sentence`
  - `vocabulary | target`
  - `grammar | structure | optional sentence`
- Candidate parsing is backward-compatible with the old TSV format.
- Candidate parsing now handles provider responses that use `provided_example`, `example`, `source_sentence`, `word`, `phrase`, or `structure` fields.
- TXT/HTML files can be imported without OCR.

## Safety

`Import Material` still never adds cards directly to Anki. It only prepares candidates and sends them to Batch / Queue for generation and review.
