# v12.3.0 — In-app Voice Library

## Piper

- Browse the online Piper catalog from inside Speech & Audio.
- Filter/search voices by language/name.
- Preview public samples with the app's internal audio player.
- Download/add the model and JSON config into `voices/piper`.
- Add an existing local `.onnx` model together with its matching `.onnx.json`.
- Installed voices are auto-discovered and become available in Voice Lab and Conversation audio selectors.

## ElevenLabs

- Browse ElevenLabs shared Voice Library using the user's own API key.
- Browse My Voices.
- Preview provider samples inside the app without opening an external player.
- Add a shared voice to the user's ElevenLabs collection and select it immediately.
- Remember selected voice IDs locally without storing the API key in the voice registry.

## Safety / product behavior

- Network access occurs only after an explicit Voice Library search/preview/download/add action.
- Piper models are not bundled into the clean release.
- Users should review the source voice/model terms before redistributing a downloaded voice.
