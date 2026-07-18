# Batch / Queue Vocabulary Mode

## Purpose

Batch mode reduces repetitive manual input when processing a vocabulary list while preserving human review before each card is added to Anki.

## Input formats

### TXT

One word or phrase per line. Empty lines and case-insensitive duplicates are removed.

### CSV

The first column is used. An optional header such as `word`, `word_or_phrase`, `phrase`, or `vocabulary` is ignored.

### Pasted text

One word or phrase per line.

## Item states

- `pending`: not generated yet;
- `ready`: generated and waiting for review;
- `added`: added to Anki;
- `skipped`: intentionally skipped;
- `invalid`: rejected by validation or generation.

## Review flow

The application generates one card at a time. The current phrase can be edited, regenerated, added to Anki, skipped, or reviewed through backward and forward navigation. Add and Skip automatically advance to the next item.

## Session persistence

A session can be saved as JSON. The file stores the items, current position, statuses, provider, languages, and selected deck. It does not store API keys.

## UX behaviour

Successful actions are displayed in the persistent status area and recent activity line. Modal dialogs are reserved for errors and warnings.


## Simple Auto Batch

The Batch / Queue tab supports two bulk actions:

- `Auto-generate pending`;
- `Add all ready`.

`Auto-generate pending` processes vocabulary items one by one and stores every
generated card payload inside the Batch session.

`Add all ready` processes ready cards one at a time through the Tk event loop.
It does not use a background worker thread. This keeps the implementation simple
and avoids direct GUI updates from worker threads.

### Autosave

Batch sessions are automatically saved to `batch_autosaves/` after list loading,
generation, invalid/error states, skip/add actions, and bulk progress.

### Duplicate handling

Before `Add all ready`, existing vocabulary notes from the selected Anki deck are
loaded once into a duplicate cache. Duplicate cards can either update the existing
note or remain in manual review, depending on the selected policy.
