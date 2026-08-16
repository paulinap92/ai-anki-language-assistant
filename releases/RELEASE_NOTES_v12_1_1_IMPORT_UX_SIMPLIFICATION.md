# v12.1.1 — Import Material UX simplification

This release removes implementation history from the main workflow without deleting the underlying extraction logic.

## User-facing changes

- `Batch / Queue` is now simply `Batch` throughout the UI.
- Import Material shows four extraction choices only:
  - Vocabulary & expressions
  - Grammar
  - Examples / sentences
  - Auto
- Each choice explains what it extracts directly in the UI.
- AI extraction is presented as the recommended path; the basic local finder remains available as a no-API fallback.

## Internal compatibility

The four choices map to the existing tested extraction contracts rather than replacing them:

- Vocabulary & expressions → Vocabulary + source examples
- Grammar → Smart grammar import
- Examples / sentences → Provided examples
- Auto → Mixed

This keeps the richer extraction behavior while making the product easier to understand.
