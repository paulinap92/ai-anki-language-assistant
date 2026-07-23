# Speech and Text-to-Speech

## Scope

The first speech milestone adds optional text-to-speech for vocabulary example sentences. Speech-to-text remains a later milestone.

## Providers

- ElevenLabs: cloud MP3 generation.
- OpenAI TTS: cloud MP3 generation.
- Gemini TTS: cloud WAV generation.
- Piper: local/offline WAV generation with a configured voice model.

Providers implement a common `TextToSpeechProvider` contract and are registered through a factory only when their credentials or local model are configured.

## Workflows

### New vocabulary card

```text
generate card
→ review example sentence
→ generate example audio on demand
→ preview audio
→ store media in Anki
→ save [sound:filename] in Audio
```

### Existing vocabulary cards

```text
select deck
→ load notes with empty Audio
→ select notes
→ generate audio
→ storeMediaFile
→ updateNoteFields
```

Existing notes retain their note IDs and review history.

## Cache

The cache key includes text, language, provider, model, and voice. Unchanged synthesis configurations reuse the existing local audio file.

## Anki model

`AI Vocabulary Light Card` includes an `Audio` field. Existing note types receive the field automatically through AnkiConnect before templates are updated.


## Diagnostics

TTS and Anki audio operations are logged to `logs/ai_anki_app.log`.

The log includes:

- provider, model, and selected voice;
- generated cache path;
- cache/provider source;
- Anki media upload;
- Audio field update;
- exception details for failed audio operations.

The GUI displays detailed error messages instead of a generic failure state.
