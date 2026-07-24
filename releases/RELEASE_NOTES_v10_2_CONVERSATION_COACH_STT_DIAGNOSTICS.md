# v10.2 — Conversation Coach + STT diagnostics

Small stabilization release for Conversation Practice after teacher/user testing.

## Conversation Coach feedback

- Reworked conversation feedback prompt to be warmer, more positive, and more teacher-like.
- Feedback now asks providers for visible corrections:
  - original learner fragment,
  - corrected fragment,
  - short explanation of how to improve it.
- Added optional `mini_practice` field to conversation feedback.
- Conversation chat now renders:
  - positive feedback,
  - `MAIN CORRECTIONS` with ❌ / ✅ / 💡,
  - corrected version,
  - stronger answer,
  - mini practice,
  - suggested expressions,
  - next question.

## Suggested expressions

- Suggested expressions are displayed in the chat and in the right-side checklist.
- `Generate queue + add to Anki` now uses the selected Conversation model and Conversation language, not the hidden global Card AI provider / Target language.

## Local Whisper / STT diagnostics

- `last_recording.wav` is kept in `.audio_cache` instead of being deleted immediately.
- Added `Play last recording` and `Open audio file` buttons in Conversation Practice.
- Added visible recording timer.
- Added `Finishing recording...` status before transcription.
- Added a short tail after Stop to avoid cutting the last words.
- Disabled faster-whisper VAD by default for this trial, so quiet/pause-heavy speech is less likely to be skipped.

## UX cleanup

- Switching tabs now refreshes the global status bar so old Conversation messages do not remain visible in Speech / Audio.
- `.env` loading now uses `override=True`, so saved `.env` values override stale OS environment variables.
- Placeholder API keys such as `your_openai_api_key_here` are ignored and not treated as configured providers.

## Still not changed

- No LangGraph.
- No cloud agent.
- No RAG.
- No full voice chat.
- Whisper/STT remains experimental until tested on a stable microphone setup.
