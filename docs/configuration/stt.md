# Speech-to-Text

Speech-to-text is used primarily to fill an editable answer field in Conversation Practice.

## Current providers

| Provider | Status | Main configuration |
|---|---|---|
| Local Whisper | Available | `STT_PROVIDER=local_whisper`, `WHISPER_MODEL` |
| OpenAI Cloud STT | Available | `STT_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_STT_MODEL` |
| Groq Cloud STT | Available | `STT_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_STT_MODEL` |

### Local Whisper

```env
STT_PROVIDER=local_whisper
WHISPER_MODEL=small
WHISPER_LANGUAGE=
```

Local Whisper uses `faster-whisper`. The model is loaded lazily rather than during application startup.

### OpenAI Cloud

```env
STT_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

If OpenAI Cloud STT is selected without a valid OpenAI API key, the STT factory does not create the service.

### Groq Cloud

```env
STT_PROVIDER=groq
GROQ_API_KEY=...
GROQ_STT_MODEL=whisper-large-v3-turbo
```

The same Groq API key can also enable the Groq LLM provider. If Groq Cloud STT is selected without a valid key, the STT factory does not create the service.

## Language and context

Conversation can pass the active language and contextual prompt/vocabulary to transcription. The transcript remains editable before it is submitted to the conversation model.

!!! important
    STT is an input aid, not an authority. Users must be able to correct a transcription before sending it.
