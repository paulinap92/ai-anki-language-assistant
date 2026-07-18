# v7.4 — No Autocall, Rate-Limit Stop, Audio Resume

This stabilization build focuses on preventing silent API usage and preserving progress after provider failures.

## Fixed

- Loading/importing a Batch list no longer generates the first item automatically.
- Moving to the next Batch item no longer generates automatically.
- Batch preview/select actions are passive; provider API calls happen only after explicit generation actions.
- Batch generation now logs the generation trigger, such as `generate_selected`, `regenerate_selected`, or `auto_generate_pending`.
- Gemini/provider quota errors are summarized in the UI instead of showing the full raw JSON payload.
- Provider quota/rate-limit errors stop Auto Batch and keep the current item as `rate_limited`.
- Added `Retry failed/rate-limited` for regenerating failed/rate-limited items with the currently selected provider.
- Existing-card audio generation now tracks per-note audio status and skips already updated notes on the next run.
- If the TTS provider fails during existing-card audio generation, switching provider and running again continues pending/failed items instead of regenerating already completed ones.
- Added explicit `Preview voice` action to generate and play a short voice sample without updating Anki.

## Still deferred

- Full editable Batch card form before adding to Anki.
- Persistent audio-progress file across full app restart.
- ElevenLabs voice availability refresh from API.
- OCR import.
- STT/microphone flow.
