# v12.1.0 — Workflow UI Cleanup

## Purpose

Reduce duplicated UI, make the input workflows self-explanatory, restore voice testing, and make transient provider failures less disruptive.

## Main changes

- `Create Card` replaces separate Single flashcard + Grammar tabs.
- Batch mode is selected before loading; clean CSV parsing respects the selected mode.
- Batch visibly explains that it is for prepared/structured input.
- Import Material visibly explains the advanced/raw-source pipeline and keeps TXT/HTML out of OCR.
- Speech / Audio restores a visible Voice Lab and plays previews in-app.
- Fix Cards audio preview also uses in-app playback.
- Import candidate extraction handles 429/timeouts/5xx/520 with concise messages, preserved state, retry button and up to two automatic retries.
- `LLMOps / LangSmith` is moved under the clearer `Advanced / LLMOps` tab label.

## Compatibility

Card-generation, Anki note models, Conversation Practice, v12.0.8 full-text vocabulary extraction and v12.0.9 canonical duplicate-target behavior are preserved.
