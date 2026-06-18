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
