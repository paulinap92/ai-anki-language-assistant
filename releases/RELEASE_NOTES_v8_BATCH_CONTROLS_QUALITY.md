# v8 Batch Controls and Quality Stabilization

This version is a targeted stabilization pass on top of the v7.4 working ZIP.
It does not rebuild the project from scratch.

## Changed

- Added Pause/Stop controls for Batch operations:
  - Auto-generate pending.
  - Retry failed/rate-limited.
  - Add all ready.
- Added Pause/Stop controls for existing-card audio generation.
- Kept generated Batch cards as drafts until the user explicitly chooses Add to Anki or Add all ready.
- Added a Batch card editor opened from the Edit card button or by double-clicking the Batch preview.
- Persisted edited Batch card fields into autosave JSON.
- Improved Batch pseudo-card previews and friendly pending/rate-limit messages.
- Improved Gemini/provider quota UX and fatal provider error handling.
- Added lightweight card quality warnings before adding to Anki.
- Improved existing-card audio progress/resume behavior:
  - skips `audio_ready` and `updated_in_anki`,
  - saves progress on pause/stop/failure,
  - keeps the final audio summary visible.
- Treated ElevenLabs as optional/premium and added the known working default voice preset:
  - `JBFqnCBsd6RMkjVDRZzb`.
- Marked the previously problematic ElevenLabs voice preset as unverified:
  - `bfGb7JTLUnZebZRiFYyq`.

## Deferred intentionally

- OCR.
- STT.
- Audio cache recovery.
- LangGraph.
