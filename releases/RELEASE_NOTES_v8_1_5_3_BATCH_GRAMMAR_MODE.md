# v8.1.5.3 — Batch Grammar Mode

Small experimental release that adds a grammar-oriented Batch workflow before OCR/STT work.

## Added

- Batch mode selector:
  - `Vocabulary`
  - `Grammar`
  - `Mixed`
- `Grammar` Batch mode generates `AI Grammar Light Card` notes using the existing grammar Anki model.
- `Mixed` mode uses a conservative heuristic to route obvious grammar structures/connectors to grammar cards and leaves ambiguous items as vocabulary.
- New grammar batch prompt: `GRAMMAR_BATCH_PROMPT_VERSION = v1-batch-grammar-structures`.
- Batch grammar preview uses the existing grammar preview layout.
- Batch grammar card editor for reviewing/editing fields before saving.
- `Add this card` and `Add all ready` can now add grammar batch cards to Anki.

## UI cleanup included

- Removed duplicate target-language selector inside Batch. Batch now uses the top-bar target language and shows only Explanation language locally.
- Renamed several buttons for clarity:
  - `Add this card`
  - `Skip this card`
  - `Generate pending`
  - `Retry problems`
- Current Batch label changed from `Current word / phrase` to `Current item`.

## Notes / limitations

- Mixed mode is intentionally conservative. It is not a full classifier.
- Grammar duplicate handling is basic: duplicates are caught by AnkiConnect and marked/handled during add.
- No OCR/STT/Piper/Ollama changes in this release.
