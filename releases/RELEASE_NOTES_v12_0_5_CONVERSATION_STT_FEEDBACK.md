# v12.0.5 — Conversation STT and feedback quality

## Included

- Full-width stacked `Clear staged`, `Send to Batch / Queue`, and `Open Batch / Queue` buttons so labels stay readable in the scrollable side panel.
- Compact Conversation coaching by default. `Corrected version`, `Stronger answer`, `Mini practice`, and duplicate suggestion blocks are hidden unless `Detailed coaching` is enabled.
- Tutor replies are constrained to short conversational answers and should avoid long domain lectures or overconfident specialist advice.
- Correction categories: genuine `error`, optional `improvement`, and `possible_transcription` for likely STT glitches.
- Context-aware faster-whisper: selected conversation language, topic, current question, recent context, active flashcards and speaking cues are used as transcription hints.
- Whisper VAD enabled and previous-segment conditioning disabled.
- New clean-install Whisper default: `small`. Existing `.env` values are preserved; users with `WHISPER_MODEL=base` can explicitly switch to `small` or `medium`.

## Not changed

- Topic-mode flashcard suggestion semantics remain unchanged.
- Flashcard-mode rotation, coverage and candidate accumulation from v12.0.4 remain unchanged.
- Conversation still requires review before any candidate is sent to Batch / Queue; nothing is written directly to Anki.
