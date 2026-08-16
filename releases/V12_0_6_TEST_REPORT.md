# v12.0.6 test report

## Validation performed

- `python -m compileall -q src` — passed.
- Conversation/export/audio targeted test set — **34 passed**.
- Full `pytest -q` collection was attempted but stopped before execution because optional provider SDKs are not installed in the sandbox (`anthropic`, `google.genai`).

## Targeted coverage

- Conversation session rotation and due/random/repeat selection.
- Flashcard-context extraction and suggestion separation.
- Flashcard conversation prompts.
- Conversation feedback field compatibility.
- New Markdown/TXT transcript rendering and UTF-8 export.
- New auto-read text selection (tutor reply / next question).

## Windows manual checks still required

- In-app playback of configured WAV and MP3 TTS providers through the local output device.
- Automatic tutor + question playback after a real AI turn.
- Stop audio and immediate microphone recording.
- Export dialog and generated `.md` / `.txt` files.
