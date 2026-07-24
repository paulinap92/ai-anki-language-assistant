# Local/free mode: Ollama + Piper

This version adds a minimal local/free path for Conversation Practice.

## Ollama Local LLM

Ollama is optional and requires no API key.

`.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
```

Useful commands:

```powershell
ollama list
ollama run gemma3:4b
```

Recommended first model from the user's current local list: `gemma3:4b`.
`nomic-embed-text` is for embeddings/RAG later, not for chat.

## Piper Local TTS

This version supports the standalone `piper.exe` workflow. Piper does not need to live inside the repository.
A clean local layout is:

```text
C:\tools\piper\piper.exe
C:\tools\piper\espeak-ng-data\
C:\tools\piper\voices\en_US-lessac-medium.onnx
C:\tools\piper\voices\en_US-lessac-medium.onnx.json
```

`.env`:

```env
PIPER_EXE_PATH=C:\tools\piper\piper.exe
PIPER_VOICE_EN=C:\tools\piper\voices\en_US-lessac-medium.onnx
```

PowerShell test outside the app:

```powershell
echo "Hello, this is a test." | C:\tools\piper\piper.exe --model C:\tools\piper\voices\en_US-lessac-medium.onnx --output_file C:\tools\piper\test.wav
start C:\tools\piper\test.wav
```

## Conversation Practice

Conversation Practice can now use:

- `Ollama Local (experimental)` as the conversation model.
- `Read question` to generate and play the current AI question with the configured TTS provider.
- Existing Whisper/STT buttons remain for later testing on a computer with a working microphone.

This is intentionally small: no cloud agent, no LangGraph, no RAG, no automatic pronunciation scoring.


## v10.1 notes

- Conversation Practice has its own Conversation language selector.
- The top Card AI provider bar is hidden in Conversation Practice to avoid confusion.
- Single Flashcard has an Audio provider selector for Piper/other configured TTS providers.
- If no microphone is detected, STT shows a friendly no-microphone message.
