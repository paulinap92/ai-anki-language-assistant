# Local / Hybrid / BYOK setup

The app now has three user-facing setup profiles in the **Setup** tab.

## Fully local

Uses local components wherever the app has a local implementation:

- AI / card generation / conversation / text candidate extraction: Ollama
- Speech-to-text: faster-whisper
- Text-to-speech: Piper
- TXT/HTML/PDF text extraction: local Python tools
- Image/scanned-PDF OCR: local Tesseract when installed
- Anki: local AnkiConnect

Cloud AI/TTS providers are ignored in this profile even if old API keys remain in `.env`.

Example `.env`:

```env
AI_SETUP_MODE=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
STT_PROVIDER=local_whisper
WHISPER_MODEL=small
PIPER_EXE_PATH=C:\tools\piper\piper.exe
PIPER_VOICE_EN=C:\tools\piper\voices\en_US-lessac-medium.onnx
```

Install the Python dependencies with:

```powershell
pip install -r requirements-local.txt
```

Ollama and Tesseract/Piper executables or voice/model files are external local tools and are not bundled into the clean release ZIP.

## Hybrid / BYOK

Use local components together with the user's own API keys. Example:

```env
AI_SETUP_MODE=hybrid
OLLAMA_MODEL=gemma3:4b
OPENAI_API_KEY=...
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
STT_PROVIDER=local_whisper
WHISPER_MODEL=small
```

Install with:

```powershell
pip install -r requirements-hybrid.txt
```

The UI shows only configured AI providers. Cloud OCR methods are shown only when the corresponding provider/key is configured.

## API / BYOK

Use the user's own configured cloud AI/TTS providers. Ollama and Piper are not activated by the provider factories in this profile. Local Whisper remains available for speech input in this release.

```env
AI_SETUP_MODE=api
OPENAI_API_KEY=...
ELEVENLABS_API_KEY=...
STT_PROVIDER=local_whisper
WHISPER_MODEL=small
```

## First-run setup

The desktop app can start with no AI provider configured. Instead of failing on startup, it opens **Setup**. From there the user can:

- choose Fully local, Hybrid / BYOK or API / BYOK;
- create/update a starter `.env`;
- import supported settings from an existing `.env`;
- open the local `.env` file;
- reload provider configuration without restarting the app;
- check whether Ollama is reachable and whether the configured model is installed.

Imported `.env` files are filtered to app-supported keys. An existing destination `.env` is backed up before importing.

## Secret handling

`.env` is ignored by Git and excluded from clean releases. The Setup screen displays only configured/missing status; it does not print API-key values.
