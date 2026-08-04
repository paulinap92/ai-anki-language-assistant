# v12.0 — Flashcard-based Conversation

## Goal

Conversation Practice now offers two explicit modes:

- **Talk about a topic** — the existing free-topic workflow.
- **Talk based on flashcards** — a conversation guided by the current Batch / Queue material.

## Flashcard source

The new mode deliberately uses the cards already loaded in the desktop application. It does not query Anki and does not require AnkiConnect.

For each usable Batch item:

- generated vocabulary cards contribute target, meaning, definition, example and collocations;
- generated grammar cards contribute structure, meaning, example and usage;
- pending Provided examples rows contribute `target | source sentence`;
- pending vocabulary/grammar rows contribute their available target/context.

Failed, invalid and skipped rows are ignored. One session uses at most 30 items.

## Conversation behavior

The tutor should:

- lead a natural conversation rather than a definition quiz;
- create opportunities to use 1–3 targets at a time;
- recycle expressions across turns;
- preserve supplied meanings/examples;
- prioritize exact flashcard targets in suggested vocabulary.

The same flashcard context is supplied to the initial question and every feedback turn.

## UI

The existing Conversation Practice tab is preserved. A new selector chooses between the two modes. In flashcard mode the topic field becomes an optional focus and the UI shows how many usable Batch / Queue items are available.
