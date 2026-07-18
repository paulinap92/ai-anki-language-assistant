# v8.1 — Existing Cards, Audio Backfill, and Topics

> Superseded UI cleanup: v8.1.1 moves missing-audio backfill fully into **Speech / Audio** and renames **Existing Cards** to **Fix Cards**. This file remains as historical notes for the first v8.1 implementation.

This release continues the v8 stabilization line. It does not rebuild the project from scratch and does not add OCR, STT, LangGraph, or audio cache recovery.

## Added

- New **Existing Cards** tab in the modern CustomTkinter GUI.
- Existing-card search directly from Anki through AnkiConnect.
- Existing-card audio audit with statuses:
  - `has_audio`
  - `missing_audio`
  - `missing_audio_field`
  - `malformed_audio`
- Existing-card dry topic tagging using Anki tags, for example:
  - `topic_character_personality_traits`
  - `topic_work_professional_life`
- Existing-card search from a pasted word list, useful for old section-based vocabulary lists.
- Manual correction workflow for one selected existing card.
- Local backup before updating an existing note in `existing_card_backups/`.
- Existing-card missing-audio backfill routed into the safe Speech / Audio batch workflow.
- Support for non-default audio field names when updating existing notes:
  - `Audio`
  - `WordAudio`
  - `ExampleAudio`
  - `SentenceAudio`
- Batch **Topic / context** field for new vocabulary lists.
- Topic-aware vocabulary prompt context for Gemini/OpenAI/Claude.
- Topic tags added to new Batch-created Anki cards.
- Lightweight topic warnings for character/personality batches.
- Additional tests for topic prompts and existing-note audio status detection.

## Changed

- The existing-card audio scanner is no longer limited conceptually to Batch autosave.
- Missing audio detection now checks Anki note fields directly.
- Audio backfill skips notes that already have `[sound:...]`.
- Notes without an audio field are reported instead of being silently ignored.
- README now documents Existing Cards, missing-audio backfill, and topic tags.

## Not changed

- OCR remains postponed.
- STT remains postponed.
- Audio cache recovery remains postponed.
- LangGraph remains postponed.
- The classic Tkinter GUI was not modified.
- Existing note types are not automatically migrated or structurally changed.
