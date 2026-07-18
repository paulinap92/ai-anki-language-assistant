# v8.1.3.3 — Fix Cards audio repair

## Added

- Added `Fix audio` / `Fix selected audio` action in the `Fix Cards` tab.
- Added one-card audio repair dialog with:
  - source text field selection,
  - target audio field selection,
  - write mode selection,
  - audio preview generation,
  - preview playback,
  - explicit `Replace audio in Anki` action.

## Safety

- Existing `[sound:...]` audio is not replaced without confirmation.
- Updates are written to the same Anki note, preserving review history.
- A local backup is written to `existing_card_backups/` before replacing audio.
- The note is tagged with `ai_audio_fixed` after successful replacement.

## Legacy cards

- Old Basic cards without a dedicated `Audio` field can use `Append/replace [sound] in target field`, usually targeting `Back`.
- Dedicated audio fields can use `Replace target field with [sound]`.

## Not changed

- No OCR.
- No STT.
- No LangGraph.
- No automatic note-type migration.
