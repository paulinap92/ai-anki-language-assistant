# v12.4.8 — Multilingual Piper + cloud STT

## Piper

- Voice Library now loads the language list from the live Piper catalog instead of limiting the filter to the original short list.
- Any Piper catalog language can be selected/typed and filtered by its real catalog language name.
- Added explicit legacy `.env` paths for German, French, Italian and Portuguese in addition to English, Spanish and Polish:
  - `PIPER_VOICE_DE`
  - `PIPER_VOICE_FR`
  - `PIPER_VOICE_IT`
  - `PIPER_VOICE_PT`
- Downloaded Piper voices remain auto-discovered from `voices/piper`, so users are not limited to those seven explicit environment variables.

## Speech-to-text

- Added a real STT provider choice in Setup:
  - **Local Whisper** (`faster-whisper`)
  - **OpenAI Cloud** (`gpt-4o-mini-transcribe` by default)
- Cloud STT reuses the existing `OPENAI_API_KEY` and sends the selected conversation language plus the same bounded conversation/topic/vocabulary context prompt used by local STT.
- The microphone recording and diagnostic WAV flow is shared by both STT providers.
- Conversation status now shows which STT provider/model produced the transcript.
- API/BYOK users can install `requirements-cloud.txt` when they do not want the local Whisper/Piper Python stack.

## Tests

- Added cloud STT request/factory tests.
- Added Piper language-catalog regression coverage for a language outside the old fixed shortlist.
- Added Piper configuration coverage for EN/ES/PL/DE/FR/IT/PT.
