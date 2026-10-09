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



## Hidden Anki audio metadata

Custom vocabulary and grammar note types include hidden metadata fields for generated audio:

- `AudioProvider`
- `AudioModel`
- `AudioVoice`
- `AudioVoiceLabel`
- `AudioSourceText`
- `AudioGeneratedAt`
- `AudioCacheKey`
- `AudioCached`
- `AudioFile`

These fields are intentionally not shown on the card templates. They are visible in Anki Browse and make later voice/model audits or regeneration workflows possible. Existing legacy/user note types receive metadata only when they already expose these fields, so audio repair remains safe for old Basic cards.

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

## Voice Lab and preview playback (v12.1)

Speech / Audio includes a dedicated Voice Lab with editable sample text, Play voice, Stop and provider diagnostics. Preview audio is decoded and played inside the application with `sounddevice` / `soundfile`; it does not open Windows Media Player or another external player.

## In-app output device

In **Speech & Audio → Voice Lab**, select an **Output device**, or leave it on
**Automatic**. Click **Refresh devices** after connecting headphones. The selection
also applies to Conversation playback and is saved locally in `.env` by device
name and host API, not by the temporary PortAudio index.

On Windows, Automatic tries the default Windows WASAPI output in shared mode,
then the system default. If a selected device disappears or fails, the same
fallback applies and the status shows which output was used. The saved selection
is retained for when that device returns. Playback failures do not invalidate the
generated audio or its cache. File decoding and opening the output run outside
the UI thread; Stop cancels pending preview playback.

Windows verification: preview WAV and MP3 audio; select headphones and restart
the app; disconnect them and check fallback; then press Stop while a preview is
being generated. Test Conversation replay with the same output selection.
