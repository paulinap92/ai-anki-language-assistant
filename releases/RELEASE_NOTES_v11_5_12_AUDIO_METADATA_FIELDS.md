# v11.5.12 — Audio Metadata Fields

## Summary

Audio generation now stores hidden TTS metadata on Anki notes whenever the note type supports it. The visible card remains unchanged: learners still see only the normal audio player / `[sound:...]` reference, while Anki Browse can show provider/model/voice audit data.

## Added

- Hidden audio metadata fields for vocabulary and grammar note types:
  - `AudioProvider`
  - `AudioModel`
  - `AudioVoice`
  - `AudioVoiceLabel`
  - `AudioSourceText`
  - `AudioGeneratedAt`
  - `AudioCacheKey`
  - `AudioCached`
  - `AudioFile`
- Metadata writing for single-card TTS export.
- Metadata writing for Fix Cards one-note audio repair.
- Metadata writing for Speech / Audio existing-card batch backfill.
- Existing-note previews now surface audio metadata when present.

## Behavior

- Custom app note types receive the new fields automatically through the normal AnkiConnect model update path.
- Existing legacy/user note types are handled safely: metadata is written only if those fields exist, so audio repair does not fail on old Basic cards.
- Text-only card updates preserve existing audio and metadata instead of wiping them.
- Metadata fields are not referenced by the card templates, so they stay hidden during review.

## Why it matters

This makes later audio audits and migrations possible:

- find cards generated with an old TTS model;
- regenerate only cards using a specific voice;
- compare OpenAI / Gemini / ElevenLabs / Piper audio usage;
- know which source sentence was synthesized;
- distinguish provider calls from cache hits.
