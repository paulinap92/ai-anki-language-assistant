# v9.1.7 — Import restore + bulk candidate review

This release restores the broader Import Material flow after the temporary sentence-only experiment.

## Import Material

- Restored **Look for words / phrases**.
- Restored **Look for sentences**.
- Restored **Optional AI assist** using the top selected Card AI provider.
- Restored the manual candidate builder.
- Candidate **type** and **source** are kept separate:
  - type: `vocabulary`, `grammar`, `provided_example`
  - source: local words, local sentences, manual, AI assist, OCR/PDF/image/TXT import
- Added OCR quality gate before local candidate extraction:
  - Good / Medium / Poor estimate
  - Poor OCR warns before producing garbage candidates
  - suggests high resolution, crop, split columns, Mistral OCR, or manual paste

## Candidate review / cherry-pick

- Added bulk actions:
  - Select all
  - Deselect all
  - Remove selected
  - Selected → word/phrase
  - Selected → grammar
  - Selected → sentence
- Kept per-card actions for fine control.

## Batch stability

- Restored visible paste textbox in Batch with a scrollable left panel.
- Fixed issue navigation after `Approve warning` + `Add this card` so resolved cards do not keep returning as problems.
- Added cards clear stale warnings/errors after successful add.

## Notes

This version uses v9.1.5 as the base and selectively keeps the stability fixes from v9.1.6 without the sentence-only regression.
