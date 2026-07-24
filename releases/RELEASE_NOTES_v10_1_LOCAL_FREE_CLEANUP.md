# v10.1 — Local/free cleanup

Small stabilization release on top of v10.0 local/free trial.

## Changed

- Conversation Practice now hides the global top card-generation bar.
- Conversation Practice has its own visible `Conversation language` selector.
- Ollama is shown as `Ollama Local (experimental)`.
- Ollama requests now receive an internal strict local-model prompt wrapper:
  - JSON only,
  - requested language only,
  - standard script for the requested language,
  - no language/script switching,
  - shorter deterministic wording.
- Single Flashcard now has a visible `Audio provider` selector for example audio.
- STT now pre-checks microphone/input devices and shows a friendly no-microphone error instead of raw `Error querying device -1`.
- Piper path/voice errors are converted into clearer user-facing messages.

## Not changed

- STT/Whisper remains a trial feature for later testing on a machine with a working microphone.
- No LangGraph, no cloud agent, no RAG, no full voice-chat workflow.
