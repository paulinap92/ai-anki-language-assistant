# v9.1.9 — Conversation STT trial

Small experimental speech-to-text addition for Conversation Practice.

## Added

- Local Whisper STT trial for Conversation Practice.
- New buttons in the conversation tab:
  - `Record answer`
  - `Stop & transcribe`
- Transcription is inserted into the existing answer textbox.
- The user can manually edit the transcript before clicking `Send`.
- Conversation Practice now has an explicit `Conversation model` selector, independent from the top card-generation provider selector.
- The selector uses configured AI providers, for example OpenAI/ChatGPT and Gemini when their API keys are present.

## Not included

This version does not add LangGraph, cloud agents, RAG, pronunciation scoring, streaming STT, or TTS for conversation. It is only a small speech input trial.

## New optional dependencies

```bash
pipenv install faster-whisper sounddevice soundfile
```

## New `.env` options

```env
STT_PROVIDER=local_whisper
WHISPER_MODEL=base
WHISPER_LANGUAGE=
```

`WHISPER_LANGUAGE` can stay empty for automatic language detection.
