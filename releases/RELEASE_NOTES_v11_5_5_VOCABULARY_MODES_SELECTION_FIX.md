# v11.5.5 — Vocabulary modes and selection fix

## What changed

- Clarified vocabulary extraction modes:
  - **Vocabulary** returns only vocabulary candidates.
  - **Vocabulary + source examples** returns vocabulary candidates with optional source sentences, never `provided_example`.
  - **Smart vocabulary** may return both `vocabulary` and `provided_example`, but not `grammar`.
- Removed hidden 80-candidate rendering truncation for AI text extraction.
- Candidate status now reports selected/visible counts clearly.
- Smart Vocabulary parser now preserves `provided_example` candidates instead of forcing everything to vocabulary.
- Strict vocabulary modes still force everything to `vocabulary` so models cannot mix in Provided Examples or Grammar by accident.

## Why

Vocabulary lessons can contain 100+ explicit items. The previous UI rendered only the first 80 candidates, which made selection counts look wrong and hid valid entries. The previous vocabulary contract was also too strict for Smart Vocabulary and too loose about source examples.

## Expected behavior

- `Vocabulary` = clean target list only.
- `Vocabulary + source examples` = vocabulary targets plus optional source context.
- `Smart vocabulary` = vocabulary plus selected source-sentence cards as `provided_example` when useful.
