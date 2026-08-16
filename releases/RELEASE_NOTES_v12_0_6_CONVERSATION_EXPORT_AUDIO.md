# v12.0.6 - Conversation export and in-app audio

## What changed

- Export the active Conversation Practice session to Markdown or TXT.
- Export includes metadata, transcript, session flashcards and accumulated new-card candidates.
- Conversation TTS now plays inside the app instead of launching the operating-system media player.
- Added manual **Read tutor reply**, **Read question** and **Stop audio** actions.
- Added independent **Auto-read tutor** and **Auto-read question** switches.
- Auto-read combines the selected tutor reply/question into one TTS request per turn so the second part does not interrupt the first.
- TTS generation runs in a background thread; playback starts only after the complete file exists and is non-empty.
- Starting microphone recording stops TTS playback first.
- **Play last recording** also uses the internal player; **Open recording folder** remains available for diagnostics.

## Notes

Conversation audio uses the TTS provider, model and voice selected in the existing Speech / Audio workflow. WAV and MP3 decoding is handled by `soundfile`; output is played with `sounddevice`.
