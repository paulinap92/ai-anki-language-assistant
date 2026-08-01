# v11.5.7 — Import Safety Rollup

## Purpose

This release rolls forward the v11.5.4–v11.5.6 fixes and adds a blocker safety fix for runaway vocabulary extraction.

## Included fixes

- Batch UI cleanup: raw provider/model JSON no longer breaks the main Batch UI.
- Vocabulary OCR contracts:
  - `Vocabulary` stays vocabulary-only.
  - `Vocabulary + source examples` stays vocabulary-only but can attach source sentences.
  - `Smart vocabulary` may return vocabulary and provided examples, but not grammar.
- Candidate selection fix: the UI no longer silently renders only the first 80 candidates.
- Source example preservation: vocabulary candidates with source examples are routed to sentence-based Batch generation as `target | sentence` so the model preserves the imported example instead of generating a new one.
- Pattern-aware validation: phrase/pattern targets such as `pensar en (alguien/algo)` should no longer get false HARD warnings just because the example uses an inflected form.
- New blocker fix: AI candidate extraction has runtime safety caps so a provider cannot return thousands of candidates and freeze the Tkinter UI.

## New import safety behavior

If a provider returns too many candidate drafts, the app refuses to render the result and shows a warning instead of trying to create thousands of UI cards.

Approximate hard caps:

- Vocabulary: 300
- Vocabulary + source examples: 250
- Smart vocabulary: 180
- Provided examples: 160
- Grammar / Smart grammar import: 140
- Mixed: 180

For large but accepted imports, candidates above the autoselect threshold are not selected by default. The user can review and select intentionally.

## Notes

This release does not implement the later LangSmith child `run_type="llm"` cost fix or the Mini Chat with Deck demo. Those remain separate TODO items.
