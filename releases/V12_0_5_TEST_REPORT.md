# v12.0.5 test report

## Automated checks

- `33 passed` across the targeted Conversation, STT, Anki conversation-reader and flashcard-context regression suite.
- Python compile check passed for `src`, `main_gui_custom.py` and `main_gui_custom_private.py`.

## Covered

- correction category parsing (`error`, `improvement`, `possible_transcription`);
- topic and flashcard Conversation prompt contracts;
- STT language override and dynamic initial-prompt forwarding;
- STT prompt length cap;
- Whisper VAD and previous-text conditioning settings;
- existing flashcard suggestion separation;
- session rotation and Anki deck conversation reading.

## Manual check still required

The final visual button layout and live microphone quality need Windows + CustomTkinter + the user's real microphone/Anki setup. No `.env` or private runtime state is included in the clean package.
