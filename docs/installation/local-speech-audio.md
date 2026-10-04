# Local speech and audio

Local speech features are optional. The application can work without them.

## Local Whisper — speech-to-text

Whisper converts microphone recordings into editable text, primarily in **Conversation Practice**.

The application uses **faster-whisper** for the local provider.

### Recommended setting

Open:

**Setup → Speech-to-text → Local Whisper**

Use:

```text
WHISPER_MODEL = small
```

The model is loaded lazily — not when the application starts.

On a new computer, the first transcription can take longer because the selected model may need to be downloaded and cached.

### What the user needs to do

For a correctly packaged EXE release, the user should **not** install Python or run `pip install faster-whisper`.

The release should contain the runtime dependency. The user only selects **Local Whisper** and allows the model download when first used.

!!! important "Packaging requirement"
    Before distributing the EXE, verify on a clean Windows computer that Local Whisper works without a Python installation. If it does not, the EXE build is incomplete and should be fixed rather than asking the end user to install Python packages.

### Microphone permission

If recording does not start:

**Windows Settings → Privacy & security → Microphone**

Allow microphone access for desktop applications.

### Cloud alternative

If the computer is too slow for Local Whisper, select:

- **OpenAI Cloud STT**, or
- **Groq Cloud STT**.

These do not require a local Whisper model but require the corresponding API key.

## Piper — local text-to-speech

Piper generates speech locally and does not need an API key after the runtime and voice are available.

For a normal user, voices should be managed from:

**Speech & Audio → Voice Library**

Recommended flow:

1. choose the Learning Profile language,
2. select a Piper voice,
3. download it,
4. preview it,
5. select it for card audio.

Do not require non-technical users to manually edit `.onnx` paths unless troubleshooting an advanced installation.

### Cloud alternatives

If Piper is unavailable, choose:

- OpenAI TTS,
- Gemini TTS,
- ElevenLabs.

## Recommended fallback order

For a non-technical user:

```text
STT:
Local Whisper
→ if slow/problematic: OpenAI Cloud STT

TTS:
Piper
→ if problematic: OpenAI TTS
```

With the recommended OpenAI setup, both cloud fallbacks use the same API key already configured for AI.
