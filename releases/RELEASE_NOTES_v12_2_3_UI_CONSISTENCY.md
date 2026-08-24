# v12.2.3 — UI consistency cleanup

This release focuses on making the application behave like one coherent product instead of exposing implementation history.

## Conversation

- Choose `Talk about a topic` or `Talk based on flashcards` first.
- Topic is not visible at all in flashcard mode.
- Flashcard source/deck/selection settings are not visible in topic mode.
- One `Start conversation` button is used for both flows.
- Tutor audio is grouped together; AI provider and Detailed coaching are visually secondary.

## Queue

- Public naming is consistently `Queue`; internal `_batch_*` implementation names are intentionally unchanged to avoid risky refactors.
- The input selector is described as `Input type`, not Queue/Batch mode.
- Progress now reports what the numbers mean, for example `Prepared 3 of 20 · 17 waiting`.
- Zero-value counters are hidden and a progress bar shows preparation progress.

## Import Material

- TXT/HTML are described as local file reading, not extraction.
- No AI/model/provider is used to read TXT/HTML.
- OCR/provider controls are hidden when the current source is plain TXT/HTML.
- AI is explicitly a separate later step: `Find candidates with AI`.

## Validation

- `python -m compileall -q src tests` passed.
- 87 UI/OCR/conversation/speech/Anki/core tests passed.
- Full pytest collection is not available in the packaging environment because optional `anthropic` and `google.genai` SDKs are not installed.
