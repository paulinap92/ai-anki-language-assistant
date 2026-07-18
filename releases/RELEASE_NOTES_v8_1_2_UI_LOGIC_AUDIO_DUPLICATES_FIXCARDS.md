# v8.1.2 — UI logic cleanup: Audio, duplicates, Fix Cards

This release is a stabilization/cleanup release. It does not add OCR, STT, LangGraph, or a full old-card migration system.

## Speech / Audio

- Renamed `Extra Anki query` to `Optional Anki filter`.
- Added field mapping controls:
  - `Source text field` — where TTS reads text from, for example `Example`, `Back`, `Front`, `Word`.
  - `Target audio field` — where `[sound:...]` is written.
  - `Write mode`:
    - `Use dedicated audio field`
    - `Append [sound] to existing field`
- Added legacy-card audio mode for old Basic cards that have no `Audio` field.
  - Example: `Source = Front`, `Target = Back`, `Write mode = Append [sound] to existing field`.
- Replaced unclear `skipped · no supported audio field` behaviour with readiness statuses:
  - `ready_for_audio`
  - `has_audio`
  - `needs_audio_field`
  - `needs_append_target_field`
  - `needs_source_text`
  - `malformed_audio`
- Added scan summary after `Find missing audio`, e.g. ready / already have audio / need target field / missing source text / malformed.
- `Pause audio` and `Stop audio` are disabled until an audio batch is actually running.
- `Select ready` selects only cards that can actually be processed with the current field mapping.

## Batch duplicates

- Replaced ambiguous `Yes/No` duplicate handling with an explicit duplicate precheck dialog.
- New choices:
  - `Add new only / skip duplicates`
  - `Update safe duplicates`
  - `Review duplicates first`
  - `Cancel`
- Duplicate precheck now scans all note types in the selected deck, not only `AI Vocabulary Light Card`.
- Legacy/Basic duplicates are marked as uncertain and are never auto-updated.
- Added clearer Batch statuses:
  - `added_to_anki`
  - `updated_in_anki`
  - `duplicate_found`
  - `duplicate_uncertain`
  - `duplicate_skipped`

## Fix Cards

- Renamed query copy to `Optional Anki filter`.
- `Find words from list` now reports how many pasted words were found and how many were not found.
- Existing-card rows now show an action status, e.g. `found`, `topic_tagged`, `saved_to_anki`.
- Topic tagging and manual save update the action status, so the tab no longer feels like “load list and nothing happens.”

## Anki client

- Added broad duplicate map scanning across all note types in a deck.
- Added legacy audio append support through `append_audio_to_note()`.
- Old notes with `[sound:...]` in non-audio fields, e.g. `Back`, are now recognized as already having audio.

## Not included

- OCR
- STT
- LangGraph
- Full old HTML-card migration
- Automatic note type conversion
- Large GUI rewrite
