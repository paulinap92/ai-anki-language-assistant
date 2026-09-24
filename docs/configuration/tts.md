# Text-to-Speech

Text-to-speech generates example audio and voice previews. TTS providers are built by `src/speech/tts/factory.py` according to the active setup profile and available configuration.

## Current providers

| Provider | Status | Main requirement |
|---|---|---|
| Piper | Available | Installed/downloaded Piper voice model; optional standalone `piper.exe` |
| OpenAI | Available | `OPENAI_API_KEY` |
| Gemini | Available | `GEMINI_API_KEY` |
| ElevenLabs | Available | `ELEVENLABS_API_KEY` |

### Piper

Piper is the local/free TTS path. The application supports configured voice paths and auto-discovery of downloaded voices from the local voice library.

Current explicit environment shortcuts include English, Spanish, Polish, German, French, Italian, and Portuguese, while voice-library discovery can support additional downloaded languages.

Example:

```env
PIPER_EXE_PATH=C:\tools\piper\piper.exe
PIPER_VOICE_EN=C:\tools\piper\voices\en_US-lessac-medium.onnx
```

### OpenAI

```env
OPENAI_API_KEY=...
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
```

### Gemini

```env
GEMINI_API_KEY=...
GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
GEMINI_TTS_VOICE=Kore
```

### ElevenLabs

```env
ELEVENLABS_API_KEY=...
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5
ELEVENLABS_VOICE_ID=...
```

!!! note
    Cloud voice generation can incur normal provider API usage. Piper stays local after the required runtime/voice files are installed.
