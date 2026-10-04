# Local speech and audio

Local speech features are optional. The application can work without them.

## Local Whisper — speech-to-text

Whisper converts what you say into text, primarily in **Conversation Practice**.

The application uses **faster-whisper**.

### Do I need to install Whisper myself?

**Normally: NO.**

If you received a correctly packaged Windows EXE, do **not** install Python and do **not** run `pip install`.

You only need to select:

**Setup → Speech-to-text → Local Whisper**

The application should contain the required runtime. The selected Whisper model is downloaded automatically when it is needed for the first time.

Useful official/reference links:

- [faster-whisper — official GitHub repository](https://github.com/SYSTRAN/faster-whisper)
- [faster-whisper releases](https://github.com/SYSTRAN/faster-whisper/releases)
- [Recommended `small` model on Hugging Face](https://huggingface.co/Systran/faster-whisper-small)

!!! note
    These links are mainly for reference or troubleshooting. A normal EXE user should not need to install faster-whisper manually.

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

Piper generates the spoken audio for flashcards locally.

### Do I need to install Piper myself?

**Normally: NO.**

For a packaged EXE release, the preferred flow is:

**Speech & Audio → Voice Library**

Then download a voice from inside the app.

Useful official/reference links:

- [Piper — current official project](https://github.com/OHF-Voice/piper1-gpl)
- [Piper releases / Windows builds](https://github.com/OHF-Voice/piper1-gpl/releases)
- [Piper voice documentation](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md)

!!! note
    The old `rhasspy/piper` repository is archived; current development is under the Open Home Foundation `OHF-Voice/piper1-gpl` project.

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
